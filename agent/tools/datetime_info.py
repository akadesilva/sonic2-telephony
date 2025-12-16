from datetime import datetime
import json

async def get_current_datetime(params):
    """Get current date, time and timezone"""
    now = datetime.now()
    
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.isoformat(),
        "timezone": str(now.astimezone().tzinfo),
        "weekday": now.strftime("%A"),
        "timestamp": int(now.timestamp())
    }

def get_tool_definition():
    """Return the tool definition for Nova Sonic"""
    return {
        "toolSpec": {
            "name": "get_current_datetime",
            "description": "Get current date, time, timezone and weekday information",
            "inputSchema": {
                "json": json.dumps({
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
        }
    }
