"""
Restaurant Order Agent - Strands Implementation
FastAPI WebSocket server for Vonage telephony integration
"""
import asyncio
import json
import logging
import os
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import boto3

from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel
from strands.experimental.bidi.tools import stop_conversation
from strands.experimental.bidi.types.events import BidiOutputEvent, BidiInputEvent, BidiAudioStreamEvent, BidiAudioInputEvent
from strands.experimental.bidi.types.io import BidiInput, BidiOutput

from strands_tools import (
    get_current_datetime,
    get_menu,
    check_availability,
    create_reservation,
    create_order,
    add_item_to_order,
    calculate_bill,
    complete_order,
    reject_order
)
from config import TIMEZONE_OFFSET
from aws_secrets import setup_credentials

# Configure logging
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

credential_refresh_task = None

def create_log_stream():
    """Create CloudWatch log stream if it doesn't exist"""
    log_group = os.getenv("OTEL_LOG_GROUP")
    if not log_group:
        logger.warning("OTEL_LOG_GROUP not set, skipping log stream creation")
        return None
    
    log_stream = "runtime-logs"
    
    try:
        logs_client = boto3.client('logs', region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        logs_client.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
        logger.info(f"Created log stream: {log_stream}")
        return log_stream
    except logs_client.exceptions.ResourceAlreadyExistsException:
        logger.info(f"Log stream already exists: {log_stream}")
        return log_stream
    except Exception as e:
        logger.warning(f"Could not create log stream: {e}")
        return None

app = FastAPI(title="Restaurant Order Agent")

@app.on_event("startup")
async def startup_event():
    global credential_refresh_task
    setup_credentials()
    credential_refresh_task = asyncio.create_task(refresh_credentials_periodically())

async def refresh_credentials_periodically():
    while True:
        await asyncio.sleep(3600)
        setup_credentials()

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
async def websocket_endpoint(websocket: WebSocket):
    # Create log stream for this session
    create_log_stream()
    
    logger.info(f"WebSocket connection from: {websocket.client}")
    await websocket.accept()
    
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # Get current date for system prompt
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')
    
    system_prompt = f"""You are Maria, a friendly restaurant host taking orders over the phone for Bella Italia Restaurant. You have a warm, professional tone and keep responses concise since people are listening, not reading.

CURRENT DATE: {current_date}
TIMEZONE: Australia/Melbourne (Current offset: {TIMEZONE_OFFSET})

Your role:
- Greet customers warmly and ask if they want dine-in or takeaway
- Present the menu and help customers choose items
- For DINE-IN: Check availability and create reservations (need date, time, party size, name, phone)
- For TAKEAWAY: Take the order, calculate bill, and provide total

Order flow:
1. Ask: dine-in or takeaway?
2. If dine-in: Get reservation details (date, time, party size, name, phone) → check availability → create reservation
3. If takeaway: Create order → get menu items → add items → calculate bill → complete order
4. Confirm all details before finalizing

Communication guidelines:
- Keep responses to 2-3 sentences maximum
- Ask for one piece of information at a time
- Confirm important details by repeating them back
- Use everyday language, be patient and helpful
- When reading menu items, mention name and price only (skip descriptions unless asked)

Remember: You're helping customers have a great experience ordering from Bella Italia!"""

    # Create Vonage IO classes
    class VonageInput(BidiInput):
        async def start(self, agent: BidiAgent) -> None:
            pass
        
        async def __call__(self):
            while True:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Vonage sends binary audio (16kHz mono PCM)
                        audio_bytes = message["bytes"]
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                        return BidiAudioInputEvent(
                            audio=audio_base64,
                            format="pcm",
                            sample_rate=16000,
                            channels=1
                        )
                    elif "text" in message:
                        # JSON control events - skip them
                        data = json.loads(message["text"])
                        if data.get("event") == "stop":
                            raise WebSocketDisconnect()
                elif message["type"] == "websocket.disconnect":
                    raise WebSocketDisconnect()
        
        async def stop(self) -> None:
            pass
    
    class VonageOutput(BidiOutput):
        async def start(self, agent: BidiAgent) -> None:
            pass
        
        async def __call__(self, event: BidiOutputEvent) -> None:
            if isinstance(event, BidiAudioStreamEvent) and event.audio:
                # event.audio is already base64 string, send directly
                await websocket.send_json({
                    "event": "media",
                    "media": {"payload": event.audio}
                })
        
        async def stop(self) -> None:
            pass

    # Create Strands BidiAgent with Nova Sonic
    model = BidiNovaSonicModel(
        region=aws_region,
        model_id="amazon.nova-2-sonic-v1:0",
        provider_config={
            "audio": {
                "input_sample_rate": 16000,
                "output_sample_rate": 16000,
                "voice": "tiffany",
            }
        },
        tools=[
            get_current_datetime,
            get_menu,
            check_availability,
            create_reservation,
            create_order,
            add_item_to_order,
            calculate_bill,
            complete_order,
            reject_order
        ],
    )

    agent = BidiAgent(
        model=model,
        tools=[
            get_current_datetime,
            get_menu,
            check_availability,
            create_reservation,
            create_order,
            add_item_to_order,
            calculate_bill,
            complete_order,
            reject_order
        ],
        system_prompt=system_prompt,
    )

    try:
        await agent.run(
            inputs=[VonageInput()], 
            outputs=[VonageOutput()]
        )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in agent: {e}", exc_info=True)
    finally:
        logger.info("Connection closed")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    host = "0.0.0.0" 
    uvicorn.run(app, host=host, port=port)
