import asyncio
import base64
import json
import uuid
import numpy as np
import time
import os
import yaml
import boto3
from scipy import signal
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver
from tools import get_all_tool_definitions, execute_tool
from config import TIMEZONE_OFFSET
from otel_instrumentation import log_model_input, log_model_output, log_model_choice
from opentelemetry import trace
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole

# Get tracer with proper scope name for AgentCore evaluations
tracer = trace.get_tracer("strands.telemetry.tracer", "1.0.0")

class NovaSonicBridge:
    def __init__(self, model_id='amazon.nova-2-sonic-v1:0', region='us-east-1'):
        self.model_id = model_id
        self.region = region
        self.client = None
        self.stream = None
        self.response = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        self.audio_queue = asyncio.Queue()
        self.scheduler_paused = asyncio.Event()
        self.scheduler_paused.set()
        self.websocket = None
        self.session_span = None  # Track session span for logging
        self.actor_id = None
        self.memory_session = None
        self.memory_session_manager = None
    
    async def clear_vonage_buffer(self):
        """Send clear command to Vonage to stop buffered audio playback"""
        if self.websocket:
            clear_command = json.dumps({"action": "clear"})
            await self.websocket.send_text(clear_command)

    def _resample_audio(self, audio_bytes, from_rate=24000, to_rate=16000):
        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
        num_samples = int(len(audio_data) * to_rate / from_rate)
        resampled = signal.resample(audio_data, num_samples)
        return resampled.astype(np.int16).tobytes()
        
    def _initialize_client(self):
        session = boto3.Session(region_name=self.region)
        credentials = session.get_credentials()
        if credentials:
            os.environ['AWS_ACCESS_KEY_ID'] = credentials.access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials.secret_key
            if credentials.token:
                os.environ['AWS_SESSION_TOKEN'] = credentials.token
        
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            auth_scheme_resolver=HTTPAuthSchemeResolver(),
            auth_schemes={"aws.auth#sigv4": SigV4AuthScheme(service="bedrock")}
        )
        self.client = BedrockRuntimeClient(config=config)
    
    async def send_event(self, event_json):
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        await self.stream.input_stream.send(event)
    
    async def start_session(self, actor_id: str = "61421783196"):
        self.actor_id = actor_id
        print(f"[MEMORY] Starting session for actor: {self.actor_id}")
        
        # Load memory config
        try:
            with open('.bedrock_agentcore.yaml', 'r') as f:
                config = yaml.safe_load(f)
                memory_id = config['agents']['restaurant_agent']['memory']['memory_id']
                print(f"[MEMORY] Using memory ID: {memory_id}")
                
            # Initialize memory session
            self.memory_session_manager = MemorySessionManager(
                memory_id=memory_id,
                region_name=self.region
            )
            
            self.memory_session = self.memory_session_manager.create_memory_session(
                actor_id=self.actor_id,
                session_id=self.prompt_name
            )
            print(f"[MEMORY] Memory session created with session_id: {self.prompt_name}")
            
            # Retrieve user preferences from long-term memory
            user_preferences = ""
            try:
                print(f"[MEMORY] Retrieving user preferences for actor: {self.actor_id}")
                preferences = await asyncio.to_thread(
                    self.memory_session.search_long_term_memories,
                    namespace_prefix=f"/users/{self.actor_id}/preferences",
                    query="user's name, food preferences, dietary restrictions, favorite dishes",
                    top_k=3
                )
                
                # Also retrieve semantic facts (where name often goes)
                print(f"[MEMORY] Retrieving semantic facts for actor: {self.actor_id}")
                facts = await asyncio.to_thread(
                    self.memory_session.search_long_term_memories,
                    namespace_prefix=f"/users/{self.actor_id}/facts",
                    query="user's name",
                    top_k=1
                )
                
                # Combine preferences and facts
                all_memories = list(preferences) + list(facts) if preferences and facts else (preferences or facts or [])
                
                if all_memories:
                    print(f"[MEMORY] Found {len(all_memories)} memory record(s)")
                    user_preferences = "\n\n========== USER PREFERENCES FROM PREVIOUS ORDERS ==========\n"
                    for idx, memory in enumerate(all_memories):
                        print(f"[MEMORY] Raw memory {idx+1} type: {type(memory)}")
                        
                        # Extract content from MemoryRecord object
                        content_text = ""
                        
                        # Check if it's a MemoryRecord object with attributes
                        if hasattr(memory, 'content'):
                            content_obj = memory.content
                            if hasattr(content_obj, 'text'):
                                content_text = content_obj.text
                            elif isinstance(content_obj, dict) and 'text' in content_obj:
                                content_text = content_obj['text']
                            else:
                                content_text = str(content_obj)
                        elif isinstance(memory, dict):
                            # Fallback for dict structure
                            if 'content' in memory:
                                content_obj = memory['content']
                                if isinstance(content_obj, dict) and 'text' in content_obj:
                                    content_text = content_obj['text']
                                else:
                                    content_text = str(content_obj)
                            elif 'text' in memory:
                                content_text = memory['text']
                        else:
                            content_text = str(memory)
                        
                        print(f"[MEMORY] Extracted text {idx+1}: {content_text[:100]}...")
                        
                        # Try to parse JSON if it's a preference object
                        final_content = content_text
                        try:
                            parsed = json.loads(content_text)
                            if isinstance(parsed, dict):
                                # Extract preference or main text
                                final_content = parsed.get('preference', parsed.get('text', content_text))
                        except (json.JSONDecodeError, TypeError):
                            final_content = content_text
                        
                        print(f"[MEMORY] Final content {idx+1}: {final_content}")
                        user_preferences += f"• {final_content}\n"
                    user_preferences += "===========================================================\n"
                    user_preferences += "IMPORTANT: Use these preferences to personalize your service. If you see the customer's name above, greet them by name!\n"
                else:
                    print(f"[MEMORY] No preferences or facts found for this user")
            except Exception as e:
                print(f"[MEMORY] Could not retrieve preferences: {e}")
        except Exception as e:
            print(f"[MEMORY] Memory initialization failed: {e}")
        
        
        if not self.client:
            self._initialize_client()
        
        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True
        
        session_start_event = '{"event":{"sessionStart":{"inferenceConfiguration":{"maxTokens":4096,"topP":0.9,"temperature":0.5}}}}'
        log_model_input(self.session_span, f"session_start: {session_start_event}")
        await self.send_event(session_start_event)
        
        prompt_start = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": "tiffany",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    },
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": {
                        "tools": get_all_tool_definitions(),
                        "toolChoice": {
                            "auto": {}
                        }
                    }
                }
            }
        }
        await self.send_event(json.dumps(prompt_start))
        
        text_content_start = f'{{"event":{{"contentStart":{{"promptName":"{self.prompt_name}","contentName":"{self.content_name}","type":"TEXT","interactive":true,"role":"SYSTEM","textInputConfiguration":{{"mediaType":"text/plain"}}}}}}}}'
        await self.send_event(text_content_start)
        
        # Get current date and use global timezone
        from datetime import datetime
        current_time = datetime.now()
        current_date = current_time.strftime('%Y-%m-%d')
        current_time_str = current_time.strftime('%H:%M:%S')
        
        system_prompt = f"""You are a friendly AI assistant helping customers order from Spice Garden Restaurant over the phone. Keep responses concise and natural.

CURRENT DATE: {current_date}
CURRENT TIME: {current_time_str}
TIMEZONE: Asia/Kolkata (Current offset: {TIMEZONE_OFFSET})
{user_preferences}
GREETING EXAMPLES:
- If this is a new customer: "Hello! Welcome to Spice Garden. Would you like dine-in or takeaway?"
- If you know the customer's name: "Hello [Name]! Welcome back to Spice Garden. Would you like dine-in or takeaway today?"
- DO NOT say "My name is" or introduce yourself with a name

Your role:
- Greet customers warmly (by name if you know it from preferences above) and ask if they want dine-in or takeaway
- **Only ask for the customer's name if you don't already know it from the preferences above**
- Present the menu and help customers choose items
- For DINE-IN: Check availability and create reservations (need date, time, party size, name, phone)
- For TAKEAWAY: Take the order, calculate bill with GST, and provide total

Order flow:
1. Greet customer (by name if known)
2. Ask: dine-in or takeaway?
3. **Only if name is NOT in preferences above**: Ask for customer's name
4. If dine-in: Get reservation details (date, time, party size, phone) → check availability → create reservation
5. If takeaway: Create order → get menu items → add items → calculate bill → complete order
6. Confirm all details before finalizing

Communication guidelines:
- Keep responses to 2-3 sentences maximum
- Ask for one piece of information at a time
- Confirm important details by repeating them back
- Use everyday language, be patient and helpful
- When reading menu items, mention name and price in rupees only (skip descriptions unless asked)
- Prices are in Indian Rupees (₹)
- After completing takeaway orders, say "You will receive an SMS with order confirmation" (don't read out order numbers)
- **If you know the customer's name from previous orders, greet them warmly by name at the start of the conversation**

Tool usage:
- Use get_menu to show menu categories or specific items
- Use check_availability before creating reservations
- Use create_order at the start of takeaway orders
- Use add_item_to_order for each menu item
- Use calculate_bill to get the total with 18% GST
- Use complete_order when customer confirms
- Use reject_order if customer cancels

Remember: You're helping customers have a great experience ordering from Spice Garden!"""

        print(system_prompt)
        text_input = json.dumps({
            "event": {
                "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                    "content": system_prompt
                }
            }
        })
        await self.send_event(text_input)
        
        text_content_end = f'{{"event":{{"contentEnd":{{"promptName":"{self.prompt_name}","contentName":"{self.content_name}"}}}}}}'
        await self.send_event(text_content_end)
        
        self.response = asyncio.create_task(self._process_responses())
    
    async def start_audio_input(self):
        audio_content_start = f'{{"event":{{"contentStart":{{"promptName":"{self.prompt_name}","contentName":"{self.audio_content_name}","type":"AUDIO","interactive":true,"role":"USER","audioInputConfiguration":{{"mediaType":"audio/lpcm","sampleRateHertz":16000,"sampleSizeBits":16,"channelCount":1,"audioType":"SPEECH","encoding":"base64"}}}}}}}}'
        await self.send_event(audio_content_start)
        # Play hello.raw as conversation starter
        try:
            with open('hello.raw', 'rb') as f:
                hello_audio = f.read()
            
            # Send hello audio in chunks
            chunk_size = 640
            for i in range(0, len(hello_audio), chunk_size):
                chunk = hello_audio[i:i + chunk_size]
                await self.send_audio_chunk(chunk)
        except FileNotFoundError:
            pass
    
    async def send_audio_chunk(self, audio_bytes):
        if not self.is_active:
            return
        
        # Don't log audio chunks - too noisy
        
        blob = base64.b64encode(audio_bytes).decode('utf-8')
        audio_event = f'{{"event":{{"audioInput":{{"promptName":"{self.prompt_name}","contentName":"{self.audio_content_name}","content":"{blob}"}}}}}}'
        await self.send_event(audio_event)
    
    async def end_audio_input(self):
        if self.stream is not None:
            audio_content_end = f'{{"event":{{"contentEnd":{{"promptName":"{self.prompt_name}","contentName":"{self.audio_content_name}"}}}}}}'
            await self.send_event(audio_content_end)
    
    async def get_audio_response(self):
        return await self.audio_queue.get()


    async def _handle_tool_use(self, tool_name, tool_use, tool_use_id):
        # Execute tool asynchronously without blocking conversation
        asyncio.create_task(self._execute_tool_async(tool_name, tool_use, tool_use_id))
    
    async def send_text(self, text):
        """Send text to Nova Sonic during conversation"""
        content_name = str(uuid.uuid4())
        
        # contentStart
        content_start = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "type": "TEXT",
                    "interactive": True,
                    "role": "USER",
                    "textInputConfiguration": {"mediaType": "text/plain"}
                }
            }
        }
        await self.send_event(json.dumps(content_start))
        
        # textInput
        text_input = {
            "event": {
                "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": text
                }
            }
        }
        await self.send_event(json.dumps(text_input))
        
        # contentEnd
        content_end = {
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name
                }
            }
        }
        await self.send_event(json.dumps(content_end))

    async def _execute_tool_async(self, tool_name, tool_use, tool_use_id):
        content_name = str(uuid.uuid4())
        try:
            
            content = json.loads(tool_use.get('content', '{}'))
            result = await execute_tool(tool_name, content)
            await self._send_tool_result(content_name, tool_use_id, result)
        except Exception as e:
            await self._send_tool_result(content_name, tool_use_id, {"error": str(e)})
    
    async def _send_tool_result(self, content_name, tool_use_id, result):
        tool_start = {
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "interactive": False,
                    "type": "TOOL",
                    "role": "TOOL",
                    "toolResultInputConfiguration": {
                        "toolUseId": tool_use_id,
                        "type": "TEXT",
                        "textInputConfiguration": {"mediaType": "text/plain"}
                    }
                }
            }
        }
        await self.send_event(json.dumps(tool_start))
        
        tool_result = {
            "event": {
                "toolResult": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": json.dumps(result)
                }
            }
        }
        await self.send_event(json.dumps(tool_result))
        
        tool_end = {
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name
                }
            }
        }
        await self.send_event(json.dumps(tool_end))
    
    async def end_session(self):
        if not self.is_active:
            return
        self.is_active = False

        if self.stream is not None:
            await self.send_event(f'{{"event":{{"promptEnd":{{"promptName":"{self.prompt_name}"}}}}}}')
            await self.send_event('{"event":{"sessionEnd":{}}}')
            await self.stream.input_stream.close()
        
        # End OTEL span
        if self.session_span:
            self.session_span.end()
        if self.response and not self.response.done():
            try:
                await asyncio.wait_for(self.response, timeout=2.0)
            except asyncio.TimeoutError:
                self.response.cancel()
            except Exception:
                pass
    
    async def _process_responses(self):
        try:
            while self.is_active:
                output = await self.stream.await_output()
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode('utf-8')
                    json_data = json.loads(response_data)
                    
                    if 'event' in json_data and 'audioOutput' in json_data['event']:
                        audio_content = json_data['event']['audioOutput']['content']
                        
                       
                        audio_bytes = base64.b64decode(audio_content)
                        resampled_audio = self._resample_audio(audio_bytes)
                        
                        chunk_size = 640
                        for i in range(0, len(resampled_audio), chunk_size):
                            chunk = resampled_audio[i:i + chunk_size]
                            await self.audio_queue.put(chunk)
                    
                    elif 'event' in json_data and 'textOutput' in json_data['event']:
                        text_output = json_data['event']['textOutput']
                        content = text_output.get('content', '')
                        role = text_output.get('role', 'UNKNOWN')
                        
                        # Log USER and ASSISTANT messages as separate events
                        if self.session_span and content:
                            if role == 'USER':
                                self.session_span.add_event(
                                    "gen_ai.user.message",
                                    attributes={
                                        "content": content[:1000],
                                        "role": "user",
                                        "completion_id": text_output.get('completionId', ''),
                                        "content_id": text_output.get('contentId', '')
                                    }
                                )
                            elif role == 'ASSISTANT':
                                self.session_span.add_event(
                                    "gen_ai.assistant.message",
                                    attributes={
                                        "content": content[:1000],
                                        "role": "assistant",
                                        "completion_id": text_output.get('completionId', ''),
                                        "content_id": text_output.get('contentId', '')
                                    }
                                )
                        
                        # Write to memory
                        if self.memory_session and content and role in ['USER', 'ASSISTANT']:
                            try:
                                message_role = MessageRole.USER if role == 'USER' else MessageRole.ASSISTANT
                                print(f"[MEMORY] Writing {role} message to memory: {content[:100]}...")
                                await asyncio.to_thread(
                                    self.memory_session.add_turns,
                                    messages=[ConversationalMessage(content, message_role)]
                                )
                                print(f"[MEMORY] Successfully wrote {role} message to memory")
                            except Exception as e:
                                print(f"[MEMORY] Failed to write to memory: {e}")
                        
                        try:
                            content_json = json.loads(content)
                            if content_json.get('interrupted'):
                                # Clear Vonage's audio buffer
                                await self.clear_vonage_buffer()
                                await asyncio.sleep(0.1)
                                
                                while not self.audio_queue.empty():
                                    try:
                                        self.audio_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break
                        except json.JSONDecodeError:
                            pass
                    
                    elif 'event' in json_data and 'toolUse' in json_data['event']:
                        tool_use = json_data['event']['toolUse']
                        
                        # Log tool use request to OTEL
                        if self.session_span:
                            log_model_choice(self.session_span, tool_use)
                        
                        asyncio.create_task(self._handle_tool_use(
                            tool_use['toolName'], tool_use, tool_use['toolUseId']
                        ))
        except Exception as e:
            print(e)
