"""
OpenTelemetry instrumentation for restaurant agent
Follows GenAI semantic conventions and AgentCore best practices
"""
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from datetime import datetime, timezone
import json
import functools
import logging

# Get tracer with proper scope name for AgentCore evaluations
tracer = trace.get_tracer("strands.telemetry.tracer", "1.0.0")
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # Only log errors

def instrument_tool(tool_name):
    """Decorator to instrument tool calls with OpenTelemetry spans"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(params):
            # Also log to standard logger for CloudWatch (errors only)
            logger.error(f"[TOOL_CALL] {tool_name} - Input: {json.dumps(params)}")
            
            with tracer.start_as_current_span(
                f"execute_tool {tool_name}",
                kind=trace.SpanKind.INTERNAL
            ) as span:
                try:
                    # Set attributes
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("gen_ai.operation.name", "execute_tool")
                    span.set_attribute("gen_ai.tool.name", tool_name)
                    
                    # Add input as event
                    span.add_event("tool_execution_started", {
                        "tool.name": tool_name,
                        "tool.input": json.dumps(params)[:500]
                    })
                    
                    result = await func(params)
                    
                    # Add result as event
                    span.add_event("tool_execution_completed", {
                        "tool.name": tool_name,
                        "tool.output": json.dumps(result)[:500],
                        "success": True
                    })
                    
                    # Set attributes for result
                    span.set_attribute("tool.status", "success")
                    span.set_status(Status(StatusCode.OK))
                    
                    
                    return result
                    
                except Exception as e:
                    # Add error event
                    span.add_event("tool_execution_failed", {
                        "tool.name": tool_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    
                    span.set_attribute("tool.status", "error")
                    span.set_attribute("tool.error", str(e))
                    span.set_attribute("tool.error_type", type(e).__name__)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    
                    logger.error(f"[TOOL_ERROR] {tool_name} - Error: {str(e)}")
                    raise
        return wrapper
    return decorator

def log_model_input(span, message_content):
    """Log model input message as event"""
    span.add_event("model_input_received", {
        "content": message_content[:500] if isinstance(message_content, str) else str(message_content)[:500]
    })

def log_model_output(span, message_content):
    """Log model output message as event"""
    span.add_event("model_output_generated", {
        "content": message_content[:500] if isinstance(message_content, str) else str(message_content)[:500]
    })

def log_model_choice(span, choice_data):
    """Log model choice (response) as event"""
    span.add_event("model_choice_made", {
        "choice": json.dumps(choice_data)[:500]
    })
