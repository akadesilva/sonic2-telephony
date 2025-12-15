from .internet_search import internet_search, get_tool_definition as get_internet_search_tool
#from .google_calendar import create_calendar_event, list_calendar_events, get_tool_definitions as get_calendar_tools
#rom .google_docs import create_google_doc, read_google_doc, append_to_google_doc, get_tool_definitions as get_docs_tools
#from .google_sheets import create_google_sheet, read_google_sheet, write_to_google_sheet, append_to_google_sheet, get_tool_definitions as get_sheets_tools

# Registry of all available tools
TOOLS = {
    "internet_search": internet_search
    
}

def get_all_tool_definitions():
    """Get all tool definitions for Nova Sonic"""
    return [
        get_internet_search_tool()
       
    ]

async def execute_tool(tool_name, tool_input):
    """Execute a tool by name"""
    if tool_name in TOOLS:
        return await TOOLS[tool_name](tool_input)
    return {"error": f"Unknown tool: {tool_name}"}

