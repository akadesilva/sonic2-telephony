import asyncio
import json
import logging
import os
import requests
from requests.exceptions import RequestException
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from nova_sonic_bridge import NovaSonicBridge

# Configure logging
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

credential_refresh_task = None

def get_imdsv2_token():
    try:
        response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        )
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None

def get_credentials_from_imds():
    result = {"success": False, "credentials": None, "role_name": None, "error": None}
    try:
        token = get_imdsv2_token()
        headers = {"X-aws-ec2-metadata-token": token} if token else {}
        
        role_response = requests.get(
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            headers=headers, timeout=2
        )
        if role_response.status_code != 200:
            result["error"] = f"Failed to retrieve IAM role name: HTTP {role_response.status_code}"
            return result
        
        role_name = role_response.text.strip()
        result["role_name"] = role_name
        
        creds_response = requests.get(
            f"http://169.254.169.254/latest/meta-data/iam/security-credentials/{role_name}",
            headers=headers, timeout=2
        )
        if creds_response.status_code != 200:
            result["error"] = f"Failed to retrieve credentials: HTTP {creds_response.status_code}"
            return result
        
        credentials = creds_response.json()
        result["success"] = True
        result["credentials"] = {
            "AccessKeyId": credentials.get("AccessKeyId"),
            "SecretAccessKey": credentials.get("SecretAccessKey"),
            "Token": credentials.get("Token"),
            "Expiration": credentials.get("Expiration")
        }
    except RequestException as e:
        result["error"] = f"Request exception: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    return result

async def refresh_credentials_from_imds():
    logger.info("Starting credential refresh background task")
    while True:
        try:
            imds_result = get_credentials_from_imds()
            if imds_result["success"]:
                creds = imds_result["credentials"]
                os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
                os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
                os.environ["AWS_SESSION_TOKEN"] = creds["Token"]
                logger.info(f"✅ Credentials refreshed, expires: {creds['Expiration']}")
                
                try:
                    expiration = datetime.fromisoformat(creds['Expiration'].replace('Z', '+00:00'))
                    now = datetime.now(expiration.tzinfo)
                    refresh_interval = min(max((expiration - now).total_seconds() - 300, 60), 3600)
                except Exception:
                    refresh_interval = 3600
                await asyncio.sleep(refresh_interval)
            else:
                logger.error(f"Failed to refresh credentials: {imds_result['error']}")
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in credential refresh: {e}")
            await asyncio.sleep(300)

app = FastAPI(title="Vonage Nova Sonic WebSocket Server")

@app.on_event("startup")
async def startup_event():
    global credential_refresh_task
    logger.info("🚀 Application starting up...")
    
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        logger.info("✅ Using credentials from environment variables")
    else:
        logger.info("🔄 Fetching credentials from IMDS...")
        imds_result = get_credentials_from_imds()
        if imds_result["success"]:
            creds = imds_result["credentials"]
            os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
            os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
            os.environ["AWS_SESSION_TOKEN"] = creds["Token"]
            logger.info(f"✅ Initial credentials loaded from IMDS")
            credential_refresh_task = asyncio.create_task(refresh_credentials_from_imds())
        else:
            logger.error(f"❌ Failed to fetch credentials: {imds_result['error']}")

@app.on_event("shutdown")
async def shutdown_event():
    global credential_refresh_task
    if credential_refresh_task and not credential_refresh_task.done():
        credential_refresh_task.cancel()
        try:
            await credential_refresh_task
        except asyncio.CancelledError:
            pass

@app.get("/health")
@app.get("/")
async def health_check():
    return JSONResponse({"status": "healthy"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info(f"WebSocket connection from: {websocket.client}")
    await websocket.accept()
    
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    nova_bridge = NovaSonicBridge(region=aws_region)
    nova_bridge.websocket = websocket
    response_task = None
    
    try:
        await nova_bridge.start_session()
        await nova_bridge.start_audio_input()
        
        # Start audio response handler
        response_task = asyncio.create_task(handle_audio_responses(websocket, nova_bridge))
        
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Binary audio from Vonage
                    await nova_bridge.send_audio_chunk(message["bytes"])
                elif "text" in message:
                    # JSON events from Vonage
                    data = json.loads(message["text"])
                    logger.info(f"Vonage event: {data.get('event')}")
                    if data.get("event") == "stop":
                        break
            elif message["type"] == "websocket.disconnect":
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if response_task:
            response_task.cancel()
        await nova_bridge.end_audio_input()
        await nova_bridge.end_session()

async def handle_audio_responses(websocket: WebSocket, nova_bridge: NovaSonicBridge):
    try:
        while nova_bridge.is_active:
            audio_response = await nova_bridge.get_audio_response()
            if audio_response:
                await websocket.send_bytes(audio_response)
    except Exception as e:
        logger.error(f"Audio response error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
