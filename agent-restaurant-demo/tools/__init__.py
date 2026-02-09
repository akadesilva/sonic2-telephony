from .datetime_info import get_current_datetime, get_tool_definition as get_datetime_tool
from .menu import get_menu, get_tool_definition as get_menu_tool
from .availability import check_availability, get_tool_definition as get_availability_tool
from .reservation import create_reservation, get_tool_definition as get_reservation_tool
from .orders import (
    create_order, add_item_to_order, calculate_bill, complete_order, reject_order,
    get_tool_definitions as get_order_tools
)
import sys
sys.path.append('..')
from otel_instrumentation import instrument_tool

# Wrap tools with instrumentation
get_current_datetime = instrument_tool("get_current_datetime")(get_current_datetime)
get_menu = instrument_tool("get_menu")(get_menu)
check_availability = instrument_tool("check_availability")(check_availability)
create_reservation = instrument_tool("create_reservation")(create_reservation)
create_order = instrument_tool("create_order")(create_order)
add_item_to_order = instrument_tool("add_item_to_order")(add_item_to_order)
calculate_bill = instrument_tool("calculate_bill")(calculate_bill)
complete_order = instrument_tool("complete_order")(complete_order)
reject_order = instrument_tool("reject_order")(reject_order)

# Registry of all available tools
TOOLS = {
    "get_current_datetime": get_current_datetime,
    "get_menu": get_menu,
    "check_availability": check_availability,
    "create_reservation": create_reservation,
    "create_order": create_order,
    "add_item_to_order": add_item_to_order,
    "calculate_bill": calculate_bill,
    "complete_order": complete_order,
    "reject_order": reject_order
}

def get_all_tool_definitions():
    """Get all tool definitions for Nova Sonic"""
    return [
        get_datetime_tool(),
        get_menu_tool(),
        get_availability_tool(),
        get_reservation_tool(),
        *get_order_tools()
    ]

async def execute_tool(tool_name, tool_input):
    """Execute a tool by name"""
    if tool_name in TOOLS:
        return await TOOLS[tool_name](tool_input)
    return {"error": f"Unknown tool: {tool_name}"}
