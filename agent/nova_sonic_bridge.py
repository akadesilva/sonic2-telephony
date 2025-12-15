import asyncio
import base64
import json
import uuid
import numpy as np
import time
import os
import boto3
from scipy import signal
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver
import requests

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
    
    async def clear_vonage_buffer(self):
        """Send clear command to Vonage to stop buffered audio playback"""
        if self.websocket:
            clear_command = json.dumps({"action": "clear"})
            await self.websocket.send_text(clear_command)
            print("Sent clear audio buffer command to Vonage")

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
            http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
            http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
        )
        self.client = BedrockRuntimeClient(config=config)
    
    async def send_event(self, event_json):
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        await self.stream.input_stream.send(event)
    
    async def start_session(self):
        if not self.client:
            self._initialize_client()
        
        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True
        
        await self.send_event('{"event":{"sessionStart":{"inferenceConfiguration":{"maxTokens":4096,"topP":0.9,"temperature":0.7}}}}')
        
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
                        "tools": [{
                            "toolSpec": {
                                "name": "internet_search",
                                "description": "Internet search with perplexity",
                                "inputSchema": {
                                    "json": json.dumps({
                                        "type": "object",
                                        "properties": {"query": {"type": "string", "description": "query to search"}},
                                        "required": ["query"]
                                    })
                                }
                            }
                        }]
                    }
                }
            }
        }
        await self.send_event(json.dumps(prompt_start))
        
        text_content_start = f'{{"event":{{"contentStart":{{"promptName":"{self.prompt_name}","contentName":"{self.content_name}","type":"TEXT","interactive":true,"role":"SYSTEM","textInputConfiguration":{{"mediaType":"text/plain"}}}}}}}}'
        await self.send_event(text_content_start)
        
        system_prompt = """You are Amy, a friendly assistant for a telephony system. Keep responses short (2-3 sentences). Greet callers warmly and ask how you can help. Use internet_search tool when needed for current information."""
        
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
            print("hello.raw file not found")
    
    async def send_audio_chunk(self, audio_bytes):
        if not self.is_active:
            return
        blob = base64.b64encode(audio_bytes).decode('utf-8')
        audio_event = f'{{"event":{{"audioInput":{{"promptName":"{self.prompt_name}","contentName":"{self.audio_content_name}","content":"{blob}"}}}}}}'
        await self.send_event(audio_event)
    
    async def end_audio_input(self):
        audio_content_end = f'{{"event":{{"contentEnd":{{"promptName":"{self.prompt_name}","contentName":"{self.audio_content_name}"}}}}}}'
        await self.send_event(audio_content_end)
    
    async def get_audio_response(self):
        return await self.audio_queue.get()

    async def internet_search(self, query):
        api_key = os.getenv("PERPLEXITY_API_KEY", "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")
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": query['query']}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        response = requests.post(url, json=payload, headers=headers)
        return response.json() if response.status_code == 200 else {"error": response.text}

    async def _handle_tool_use(self, tool_name, tool_use, tool_use_id):
        content_name = str(uuid.uuid4())
        try:
            if tool_name == "internet_search":
                content = json.loads(tool_use.get('content', '{}'))
                result = await self.internet_search(content)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
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

        await self.send_event(f'{{"event":{{"promptEnd":{{"promptName":"{self.prompt_name}"}}}}}}')
        await self.send_event('{"event":{"sessionEnd":{}}}')
        await self.stream.input_stream.close()
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
                        content = json_data['event']['textOutput'].get('content', '')
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
                        asyncio.create_task(self._handle_tool_use(
                            tool_use['toolName'], tool_use, tool_use['toolUseId']
                        ))
        except Exception as e:
            print(f"Error processing responses: {e}")
