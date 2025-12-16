from .internet_search import internet_search, get_tool_definition as get_internet_search_tool
from .google_calendar import create_calendar_event, list_calendar_events, update_calendar_event, delete_calendar_event, get_tool_definitions as get_calendar_tools
from .notes import read_notes, update_notes, get_tool_definitions as get_notes_tools
from .datetime_info import get_current_datetime, get_tool_definition as get_datetime_tool

# Registry of all available tools
TOOLS = {
    "internet_search": internet_search,
    "create_calendar_event": create_calendar_event,
    "list_calendar_events": list_calendar_events,
    "update_calendar_event": update_calendar_event,
    "delete_calendar_event": delete_calendar_event,
    "read_notes": read_notes,
    "update_notes": update_notes,
    "get_current_datetime": get_current_datetime
}

def get_all_tool_definitions():
    """Get all tool definitions for Nova Sonic"""
    return [
        get_internet_search_tool(),
        *get_calendar_tools(),
        *get_notes_tools(),
        get_datetime_tool()
    ]

async def execute_tool(tool_name, tool_input):
    """Execute a tool by name"""
    if tool_name in TOOLS:
        return await TOOLS[tool_name](tool_input)
    return {"error": f"Unknown tool: {tool_name}"}

