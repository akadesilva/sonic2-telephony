import sys
sys.path.append('..')
from restaurant_data import RESERVATIONS, AVAILABILITY
from datetime import datetime
import json

async def create_reservation(params):
    """Create a table reservation"""
    print(f"[TOOL] create_reservation called with params: {params}")
    date = params.get("date")
    time = params.get("time")
    party_size = params.get("party_size")
    name = params.get("name")
    phone = params.get("phone")
    
    if not all([date, time, party_size, name]):
        return {"error": "Date, time, party size, and name are required"}
    
    # Check availability
    if date not in AVAILABILITY or time not in AVAILABILITY[date]:
        return {"error": f"Invalid date or time slot"}
    
    if AVAILABILITY[date][time] <= 0:
        return {"error": f"No tables available at {time} on {date}"}
    
    # Create reservation
    reservation_id = f"RES{len(RESERVATIONS) + 1:04d}"
    reservation = {
        "reservation_id": reservation_id,
        "date": date,
        "time": time,
        "party_size": party_size,
        "name": name,
        "phone": phone,
        "status": "confirmed",
        "created_at": datetime.now().isoformat()
    }
    
    RESERVATIONS.append(reservation)
    AVAILABILITY[date][time] -= 1  # Reduce available tables
    
    print(f"[TOOL] create_reservation: Created {reservation_id} for {name}")
    return {
        "success": True,
        "reservation": reservation,
        "message": f"Reservation confirmed for {name}, party of {party_size}, on {date} at {time}. Reservation ID: {reservation_id}"
    }

def get_tool_definition():
    return {
        "toolSpec": {
            "name": "create_reservation",
            "description": "Create a table reservation for dine-in customers",
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
                            "description": "Time in HH:MM format"
                        },
                        "party_size": {
                            "type": "integer",
                            "description": "Number of people"
                        },
                        "name": {
                            "type": "string",
                            "description": "Customer name for the reservation"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Contact phone number"
                        }
                    },
                    "required": ["date", "time", "party_size", "name"]
                })
            }
        }
    }
