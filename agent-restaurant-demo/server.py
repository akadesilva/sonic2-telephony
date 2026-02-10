import asyncio
import json
import logging
import os
import requests
from requests.exceptions import RequestException
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from nova_sonic_bridge import NovaSonicBridge
from aws_secrets import setup_credentials
import boto3
import uuid
from opentelemetry import baggage, context, trace

# Disable all logging to CloudWatch
logging.disable(logging.CRITICAL)  # Disable all logging
logger = logging.getLogger(__name__)

# Disable bedrock-agentcore SDK logging
logging.getLogger('bedrock_agentcore').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)

# Get OTEL tracer with proper scope name for AgentCore evaluations
tracer = trace.get_tracer("strands.telemetry.tracer", "1.0.0")

credential_refresh_task = None

def create_log_stream():
    """Create CloudWatch log stream if it doesn't exist
    log_group = os.getenv("OTEL_LOG_GROUP")
    if not log_group:
        return None
    
    log_stream = "runtime-logs"
    
    try:
        logs_client = boto3.client('logs', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        logs_client.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
        return log_stream
    except logs_client.exceptions.ResourceAlreadyExistsException:
        # Stream already exists, silently continue
        return log_stream
    except Exception as e:
        logger.warning(f"Could not create log stream: {e}")
        return None
    """
    return "runtime-logs"

    
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
    while True:
        try:
            imds_result = get_credentials_from_imds()
            if imds_result["success"]:
                creds = imds_result["credentials"]
                os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
                os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
                os.environ["AWS_SESSION_TOKEN"] = creds["Token"]
                
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
    
    # Setup secrets and credentials
    setup_credentials()
    
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        pass  # Using credentials from environment
    else:
        imds_result = get_credentials_from_imds()
        if imds_result["success"]:
            creds = imds_result["credentials"]
            os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
            os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
            os.environ["AWS_SESSION_TOKEN"] = creds["Token"]
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

@app.get("/ping")
@app.get("/")
async def health_check():
    return JSONResponse({"status": "healthy"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, caller: str = "61421783196"):
    # Generate unique session ID for this call
    session_id = f"session-{uuid.uuid4()}"
    
    # Set session ID in OTEL baggage
    ctx = baggage.set_baggage("session.id", session_id)
    token = context.attach(ctx)
    
    # Create log stream for this session
    log_stream = create_log_stream()
    
    
    # Create root span for entire session (agent invocation)
    with tracer.start_as_current_span(
        "invoke_agent restaurant_order_agent",
        kind=trace.SpanKind.INTERNAL
    ) as session_span:
        try:
            # Set required attributes for AgentCore evaluations
            session_span.set_attribute("session.id", session_id)
            session_span.set_attribute("gen_ai.operation.name", "invoke_agent")
            session_span.set_attribute("gen_ai.agent.name", "restaurant_order_agent")
            session_span.set_attribute("gen_ai.system", "aws.bedrock")
            session_span.set_attribute("gen_ai.request.model", "amazon.nova-2-sonic-v1:0")
            session_span.set_attribute("gen_ai.event.start_time", datetime.now(timezone.utc).isoformat())
            
            # Add session start event
            session_span.add_event("session_started", {
                "session.id": session_id,
                "client": str(websocket.client)
            })
            
            await websocket.accept()
            aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            nova_bridge = NovaSonicBridge(region=aws_region)
            nova_bridge.websocket = websocket
            nova_bridge.session_span = session_span  # Pass span to bridge
            response_task = None
            
            try:
                await nova_bridge.start_session(actor_id=caller)
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
                            if data.get("event") == "stop":
                                break
                            # Skip logging other Vonage control events
                    elif message["type"] == "websocket.disconnect":
                        break
                        
            except WebSocketDisconnect:
                session_span.add_event("session_disconnected", {"reason": "client_disconnect"})
            except Exception as e:
                logger.error(f"Error: {e}")
                session_span.add_event("session_error", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                session_span.set_attribute("error", str(e))
                session_span.set_attribute("error_type", type(e).__name__)
                session_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                session_span.record_exception(e)
            finally:
                await nova_bridge.end_audio_input()
                await nova_bridge.end_session()
                if response_task:
                    response_task.cancel()
                    try:
                        await response_task
                    except asyncio.CancelledError:
                        pass
                
                # Add session end event and timestamp
                session_span.set_attribute("gen_ai.event.end_time", datetime.now(timezone.utc).isoformat())
                session_span.add_event("session_ended", {"session.id": session_id})
                session_span.set_status(trace.Status(trace.StatusCode.OK))
        finally:
            # Detach context
            context.detach(token)

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
