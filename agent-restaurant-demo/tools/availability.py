import sys
sys.path.append('..')
from restaurant_data import AVAILABILITY
import json

async def check_availability(params):
    """Check table availability for a specific date and time"""
    print(f"[TOOL] check_availability called with params: {params}")
    date = params.get("date")
    time = params.get("time")
    party_size = params.get("party_size", 2)
    
    if not date or not time:
        return {"error": "Date and time are required"}
    
    if date not in AVAILABILITY:
        return {
            "available": False,
            "message": f"No availability data for {date}. Please choose another date."
        }
    
    if time not in AVAILABILITY[date]:
        return {
            "available": False,
            "message": f"Time slot {time} not available. Available times: {', '.join(AVAILABILITY[date].keys())}"
        }
    
    available_tables = AVAILABILITY[date][time]
    
    if available_tables > 0:
        result = {
            "available": True,
            "date": date,
            "time": time,
            "party_size": party_size,
            "available_tables": available_tables,
            "message": f"Yes, we have {available_tables} table(s) available for {party_size} people at {time} on {date}"
        }
        print(f"[TOOL] check_availability: Available - {available_tables} tables")
        return result
    else:
        # Suggest alternative times
        alternatives = [t for t, tables in AVAILABILITY[date].items() if tables > 0]
        print(f"[TOOL] check_availability: Not available, alternatives: {alternatives}")
        return {
            "available": False,
            "date": date,
            "time": time,
            "message": f"Sorry, no tables available at {time}. Alternative times: {', '.join(alternatives)}"
        }

def get_tool_definition():
    return {
        "toolSpec": {
            "name": "check_availability",
            "description": "Check if tables are available for a specific date, time, and party size",
            "inputSchema": {
                "json": json.dumps({
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format"
                        },
                        "time": {
                            "type": "string",
                            "description": "Time in HH:MM format (e.g., 18:00, 19:30)"
                        },
                        "party_size": {
                            "type": "integer",
                            "description": "Number of people in the party"
                        }
                    },
                    "required": ["date", "time"]
                })
            }
        }
    }
