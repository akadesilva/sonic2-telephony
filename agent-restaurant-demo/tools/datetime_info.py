from datetime import datetime
from config import TIMEZONE_OFFSET
import json

async def get_current_datetime(params):
    """Get current date and time"""
    print(f"[TOOL] get_current_datetime called")
    now = datetime.now()
    result = {
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "day_of_week": now.strftime("%A"),
        "timezone": f"Australia/Melbourne ({TIMEZONE_OFFSET})"
    }
    print(f"[TOOL] get_current_datetime result: {result}")
    return result

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

