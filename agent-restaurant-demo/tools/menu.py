import sys
sys.path.append('..')
from restaurant_data import MENU
import json

async def get_menu(params):
    """Get restaurant menu"""
    print(f"[TOOL] get_menu called with params: {params}")
    category = params.get("category")
    
    if category and category in MENU:
        result = {
            "category": category,
            "items": MENU[category]
        }
        print(f"[TOOL] get_menu returning category: {category}")
        return result
    
    # Return full menu
    print(f"[TOOL] get_menu returning full menu")
    return {
        "menu": MENU,
        "categories": list(MENU.keys())
    }

def get_tool_definition():
    return {
        "toolSpec": {
            "name": "get_menu",
            "description": "Get the restaurant menu. Can retrieve full menu or specific category (appetizers, mains, desserts, drinks)",
            "inputSchema": {
                "json": json.dumps({
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional: specific category to retrieve (appetizers, mains, desserts, drinks)",
                            "enum": ["appetizers", "mains", "desserts", "drinks"]
                        }
                    },
                    "required": []
                })
            }
        }
    }
