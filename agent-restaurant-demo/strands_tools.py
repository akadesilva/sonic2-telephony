"""
Strands-compatible tools for restaurant agent
"""
from datetime import datetime
from strands.tools.decorator import tool
from config import TIMEZONE_OFFSET
from restaurant_data import MENU, AVAILABILITY, RESERVATIONS, ORDERS, TAX_RATE
import uuid

@tool
@tool
async def get_current_datetime() -> dict:
    """Get the current date and time in Australia/Melbourne timezone"""
    now = datetime.now()
    return {
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "day_of_week": now.strftime("%A"),
        "timezone": f"Australia/Melbourne ({TIMEZONE_OFFSET})"
    }


@tool
async def get_menu(category: str = None) -> dict:
    """Get the restaurant menu. Can retrieve full menu or specific category (appetizers, mains, desserts, drinks)"""
    if category and category in MENU:
        return {
            "category": category,
            "items": MENU[category]
        }
    return {
        "menu": MENU,
        "categories": list(MENU.keys())
    }


@tool
async def check_availability(date: str, time: str, party_size: int = 2) -> dict:
    """Check if tables are available for a specific date, time, and party size"""
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
        return {
            "available": True,
            "date": date,
            "time": time,
            "party_size": party_size,
            "available_tables": available_tables,
            "message": f"Yes, we have {available_tables} table(s) available for {party_size} people at {time} on {date}"
        }
    else:
        alternatives = [t for t, tables in AVAILABILITY[date].items() if tables > 0]
        return {
            "available": False,
            "date": date,
            "time": time,
            "message": f"Sorry, no tables available at {time}. Alternative times: {', '.join(alternatives)}"
        }


@tool
async def create_reservation(date: str, time: str, party_size: int, name: str, phone: str = None) -> dict:
    """Create a table reservation for dine-in customers"""
    if not all([date, time, party_size, name]):
        return {"error": "Date, time, party size, and name are required"}
    
    if date not in AVAILABILITY or time not in AVAILABILITY[date]:
        return {"error": f"Invalid date or time slot"}
    
    if AVAILABILITY[date][time] <= 0:
        return {"error": f"No tables available at {time} on {date}"}
    
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
    AVAILABILITY[date][time] -= 1
    
    return {
        "success": True,
        "reservation": reservation,
        "message": f"Reservation confirmed for {name}, party of {party_size}, on {date} at {time}. Reservation ID: {reservation_id}"
    }


@tool
async def create_order(order_type: str, customer_name: str = None) -> dict:
    """Create a new order for dine-in or takeaway"""
    order_id = str(uuid.uuid4())[:8].upper()
    
    order = {
        "order_id": order_id,
        "order_type": order_type,
        "customer_name": customer_name,
        "items": [],
        "subtotal": 0.0,
        "tax": 0.0,
        "total": 0.0,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    ORDERS[order_id] = order
    
    return {
        "success": True,
        "order_id": order_id,
        "order_type": order_type,
        "message": f"Order {order_id} created for {order_type}"
    }


@tool
async def add_item_to_order(order_id: str, item_id: str, quantity: int = 1) -> dict:
    """Add a menu item to an existing order"""
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    item = None
    for category in MENU.values():
        for menu_item in category:
            if menu_item["id"] == item_id:
                item = menu_item
                break
        if item:
            break
    
    if not item:
        return {"error": f"Item {item_id} not found in menu"}
    
    order_item = {
        "item_id": item["id"],
        "name": item["name"],
        "price": item["price"],
        "quantity": quantity,
        "subtotal": item["price"] * quantity
    }
    
    ORDERS[order_id]["items"].append(order_item)
    
    return {
        "success": True,
        "order_id": order_id,
        "item_added": order_item,
        "message": f"Added {quantity}x {item['name']} to order"
    }


@tool
async def calculate_bill(order_id: str) -> dict:
    """Calculate the total bill for an order including tax"""
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    order = ORDERS[order_id]
    
    subtotal = sum(item["subtotal"] for item in order["items"])
    tax = subtotal * TAX_RATE
    total = subtotal + tax
    
    order["subtotal"] = round(subtotal, 2)
    order["tax"] = round(tax, 2)
    order["total"] = round(total, 2)
    
    return {
        "order_id": order_id,
        "items": order["items"],
        "subtotal": order["subtotal"],
        "tax": order["tax"],
        "total": order["total"],
        "message": f"Total bill: ${order['total']:.2f} (including ${order['tax']:.2f} tax)"
    }


@tool
async def complete_order(order_id: str) -> dict:
    """Complete and finalize an order"""
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    order = ORDERS[order_id]
    
    if not order["items"]:
        return {"error": "Cannot complete order with no items"}
    
    if order["total"] == 0.0:
        await calculate_bill(order_id)
    
    order["status"] = "completed"
    order["completed_at"] = datetime.now().isoformat()
    
    return {
        "success": True,
        "order_id": order_id,
        "order": order,
        "message": f"Order {order_id} completed. Total: ${order['total']:.2f}"
    }


@tool
async def reject_order(order_id: str, reason: str = "Customer cancelled") -> dict:
    """Reject or cancel an order"""
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    ORDERS[order_id]["status"] = "rejected"
    ORDERS[order_id]["rejection_reason"] = reason
    ORDERS[order_id]["rejected_at"] = datetime.now().isoformat()
    
    return {
        "success": True,
        "order_id": order_id,
        "message": f"Order {order_id} has been cancelled"
    }
