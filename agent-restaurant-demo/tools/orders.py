import sys
sys.path.append('..')
from restaurant_data import ORDERS, MENU, TAX_RATE
from datetime import datetime
import uuid
import json

async def create_order(params):
    """Create a new order"""
    print(f"[TOOL] create_order called with params: {params}")
    order_type = params.get("order_type", "takeaway")  # dine-in or takeaway
    customer_name = params.get("customer_name")
    
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
    
    print(f"[TOOL] create_order: Created order {order_id} ({order_type})")
    return {
        "success": True,
        "order_id": order_id,
        "order_type": order_type,
        "message": f"Order {order_id} created for {order_type}"
    }

async def add_item_to_order(params):
    """Add item to an existing order"""
    print(f"[TOOL] add_item_to_order called with params: {params}")
    order_id = params.get("order_id")
    item_id = params.get("item_id")
    quantity = params.get("quantity", 1)
    
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    # Find item in menu
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
    
    # Add to order
    order_item = {
        "item_id": item["id"],
        "name": item["name"],
        "price": item["price"],
        "quantity": quantity,
        "subtotal": item["price"] * quantity
    }
    
    ORDERS[order_id]["items"].append(order_item)
    
    print(f"[TOOL] add_item_to_order: Added {quantity}x {item['name']} to order {order_id}")
    return {
        "success": True,
        "order_id": order_id,
        "item_added": order_item,
        "message": f"Added {quantity}x {item['name']} to order"
    }

async def calculate_bill(params):
    """Calculate total bill for an order"""
    print(f"[TOOL] calculate_bill called with params: {params}")
    order_id = params.get("order_id")
    
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    order = ORDERS[order_id]
    
    subtotal = sum(item["subtotal"] for item in order["items"])
    tax = subtotal * TAX_RATE
    total = subtotal + tax
    
    order["subtotal"] = round(subtotal, 2)
    order["tax"] = round(tax, 2)
    order["total"] = round(total, 2)
    
    print(f"[TOOL] calculate_bill: Order {order_id} total = ${order['total']:.2f}")
    return {
        "order_id": order_id,
        "items": order["items"],
        "subtotal": order["subtotal"],
        "tax": order["tax"],
        "total": order["total"],
        "message": f"Total bill: ${order['total']:.2f} (including ${order['tax']:.2f} tax)"
    }

async def complete_order(params):
    """Complete and finalize an order"""
    print(f"[TOOL] complete_order called with params: {params}")
    order_id = params.get("order_id")
    
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    order = ORDERS[order_id]
    
    if not order["items"]:
        return {"error": "Cannot complete order with no items"}
    
    # Calculate final bill if not done
    if order["total"] == 0.0:
        await calculate_bill({"order_id": order_id})
    
    order["status"] = "completed"
    order["completed_at"] = datetime.now().isoformat()
    
    print(f"[TOOL] complete_order: Order {order_id} completed, total ${order['total']:.2f}")
    return {
        "success": True,
        "order_id": order_id,
        "order": order,
        "message": f"Order {order_id} completed. Total: ${order['total']:.2f}"
    }

async def reject_order(params):
    """Reject or cancel an order"""
    print(f"[TOOL] reject_order called with params: {params}")
    order_id = params.get("order_id")
    reason = params.get("reason", "Customer cancelled")
    
    if order_id not in ORDERS:
        return {"error": f"Order {order_id} not found"}
    
    ORDERS[order_id]["status"] = "rejected"
    ORDERS[order_id]["rejection_reason"] = reason
    ORDERS[order_id]["rejected_at"] = datetime.now().isoformat()
    
    print(f"[TOOL] reject_order: Order {order_id} cancelled - {reason}")
    return {
        "success": True,
        "order_id": order_id,
        "message": f"Order {order_id} has been cancelled"
    }

def get_tool_definitions():
    return [
        {
            "toolSpec": {
                "name": "create_order",
                "description": "Create a new order for dine-in or takeaway",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "order_type": {
                                "type": "string",
                                "description": "Type of order: dine-in or takeaway",
                                "enum": ["dine-in", "takeaway"]
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Customer name"
                            }
                        },
                        "required": ["order_type"]
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "add_item_to_order",
                "description": "Add a menu item to an existing order",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID"
                            },
                            "item_id": {
                                "type": "string",
                                "description": "Menu item ID (e.g., main1, app2)"
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "Quantity of the item"
                            }
                        },
                        "required": ["order_id", "item_id"]
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "calculate_bill",
                "description": "Calculate the total bill for an order including tax",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID"
                            }
                        },
                        "required": ["order_id"]
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "complete_order",
                "description": "Complete and finalize an order",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID"
                            }
                        },
                        "required": ["order_id"]
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "reject_order",
                "description": "Reject or cancel an order",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for rejection"
                            }
                        },
                        "required": ["order_id"]
                    })
                }
            }
        }
    ]
