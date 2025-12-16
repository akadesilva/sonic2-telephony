# Nova Sonic 2 Telephony Agent

A voice-based personal assistant powered by Amazon Nova Sonic 2, capable of managing calendars, taking notes, and searching the internet over phone calls.

## Key Learnings

### Handling High-Jitter Telephony Networks

Telephony networks like PSTN introduce significant jitter compared to standard internet connections. This presents unique challenges:

**The Buffer Dilemma:**
- **Larger buffers needed**: High jitter requires larger playback buffers to prevent audio dropouts
- **Barge-in interference**: Larger buffers delay interrupt detection - queued audio chunks must play before the system recognizes user interruption
- **Solution**: Vonage and Twilio provide a "clear buffer" capability that must be called when Nova Sonic sends an interrupt event

**Implementation:**
1. When Nova Sonic detects interruption, it sends an interrupt event
2. Immediately call Vonage's clear buffer API to flush queued audio on the telephony provider side
3. Discard any audio packets not yet sent to the telephony provider
4. This enables responsive barge-in despite the larger buffers

### Proactive Conversation Start

Instead of waiting for the user to speak first (which can be awkward on a phone call), we send a static `hello.raw` audio file immediately after connection. This:
- Greets the user naturally: "Hello! How can I help you today?"
- Eliminates the "dead air" moment
- Makes the interaction feel more natural and phone-like
- Triggers Nova Sonic to start the conversation flow

## Features

- **Voice Conversations**: Natural phone-based interactions using Amazon Nova Sonic 2
- **Calendar Management**: Create, list, update, and delete Google Calendar events
- **Daily Notes**: Read and update date-based notes stored in Google Drive
- **Internet Search**: Search for current information using Perplexity API
- **Date/Time Awareness**: Automatic timezone handling (Australia/Melbourne)

## Architecture

### Signalling path
```
PSTN → Vonage → API Gateway → Lambda
                                         
```


### Media path
```
PSTN → Vonage → Agent Core → Google APIs, Perplexity APIs, other tools
                                         
```

## Prerequisites

- **AWS Account** with Bedrock access (Nova Sonic 2 model)
- **Google Cloud Project** with Calendar, Docs, and Drive APIs enabled
- **Perplexity API key** for internet search
- **Vonage account** for telephony


## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

This installs:
- `bedrock-agentcore` - Amazon Bedrock AgentCore SDK
- `bedrock-agentcore-starter-toolkit` - Deployment toolkit
- `boto3` - AWS SDK for Python
- Google API libraries for Calendar, Docs, and Drive

### 2. Setup Google APIs

Follow the detailed guide: [setup/tools/google/GOOGLE_SETUP.md](setup/tools/google/GOOGLE_SETUP.md)

This generates `token.json` in the setup/tools/google directory with Calendar, Docs, and Drive permissions. This is needed in the next step.

### 3. Configure Secrets

Store your Google token in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name "sonic2-telephony/google-token" \
  --secret-string file://token.json \
  --region us-east-1
```

Store your Perplexity API key:

```bash
aws secretsmanager create-secret \
  --name "sonic2-telephony/perplexity-api-key" \
  --secret-string "xxxxx" \
  --region us-east-1
```

### 4. Deploy Agent

```bash
cd agent
agentcore configure -e server.py -n sonic2_telephony_agent
```

- Execution Role: Enter to auto create
- ECR Repository URI: Enter to auto create
- Dependency file: keep the auto detected requirements.txt
- Configure OAuth authorizer instead: No
- Configure request header allowlist?: Yes
- Enter allowed request headers: X-Amzn-Bedrock-AgentCore-Runtime-Custom-Caller
- Enable long term memory extraction: No


```bash
agentcore launch
```

The agent will be deployed as a container on AWS using the Bedrock AgentCore Starter Toolkit.

**Important:** Note the Runtime ARN from the output - you'll need it for the next step.

### 5. Update Agent Execution Role Permissions

The agent needs permission to read secrets from AWS Secrets Manager. Update the execution role:

```bash
# Get the execution role name from the AgentCore deployment
# It will be in the format: BedrockAgentCoreExecutionRole-xxxxx

# Attach the secrets policy
aws iam put-role-policy \
  --role-name BedrockAgentCoreExecutionRole-xxxxx \
  --policy-name SecretsManagerAccess \
  --policy-document file://secrets-policy.json
```

The `secrets-policy.json` file grants read access to the Google token and Perplexity API key secrets.

### 6. Deploy Vonage Telephony Integration

#### 6.1 Setup Vonage Account

1. **Create Vonage Account**
   - Go to [Vonage API Dashboard](https://dashboard.nexmo.com/)
   - Sign up for a free account
   - Verify your email

2. **Create a Vonage Application**
   - Navigate to **Applications** in the dashboard
   - Click **Create a new application**
   - Application name: `Nova Sonic Agent`
   - Select **Voice** capability
   - Under **Voice**:
     - Answer URL: Enter a placeholder (e.g., `https://example.com/answer`)
     - Answer URL HTTP Method: `POST`
     - Event URL: Enter a placeholder (e.g., `https://example.com/event`)
     - Event URL HTTP Method: `POST`
   - Click **Generate new application**
   - **Save the Application ID**

3. **Get a Phone Number**
   - Navigate to **Numbers** → **Buy numbers**
   - Select your country
   - Choose **Voice** capability
   - Select a number (mobile or landline)
   - Click **Buy**

4. **Link Number to Application**
   - Navigate to **Numbers** → **Your numbers**
   - Find your purchased number
   - Click **Edit** (pencil icon)
   - Under **Voice**, select your application: `Nova Sonic Agent`
   - Click **Ok**

5. **Get Signature Secret (Optional but Recommended)**
   - Go to your application settings
   - Navigate to **API Settings** → **Signed Webhooks**
   - Copy the signature secret
   - You'll use this in the next step

#### 6.2 Deploy Infrastructure

Deploy the API Gateway and Lambda functions to handle phone calls:

```bash
# Install CDK CLI if not already installed
npm install -g aws-cdk

# Install infrastructure dependencies
cd infrastructure
pip install -r requirements.txt

# Deploy with your Runtime ARN from step 4
export RUNTIME_ARN="arn:aws:bedrock:us-east-1:123456789012:agent-runtime/your_runtime_id"
export VONAGE_SIGNATURE_SECRET="your_signature_secret"  # From step 6.1.5
export ALLOWED_CALLER_NUMBER="61421111111"  # Restrict to your phone number (format: country code + number)
./deploy.sh
```

This deploys:
- API Gateway with `/answer` and `/event` endpoints
- Lambda functions to handle Vonage webhooks
- IAM roles with necessary permissions

**Save the output URLs:**
- Answer URL: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/answer`
- Event URL: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/event`

#### 6.3 Update Vonage Webhook URLs

Go back to your Vonage application and update the webhook URLs:

1. Navigate to **Applications** in the Vonage dashboard
2. Select your `Nova Sonic Agent` application
3. Under **Voice**:
   - Answer URL: Paste the Answer URL from step 6.2
   - Event URL: Paste the Event URL from step 6.2
4. Click **Save**

#### 6.4 Test Your Setup

Call your Vonage number! You should:
1. Hear the agent say "Hello! How can I help you today?"
2. Be able to have a natural conversation
3. Ask the agent to check your calendar, add notes, or search the internet

For detailed instructions, see [infrastructure/README.md](infrastructure/README.md).

### 7. Test Tools Locally

```bash
# Test calendar tools
python tests/test_calendar.py

# Test notes tools
python tests/test_notes.py
```

## Configuration

### Timezone

Edit `agent/config.py` to change timezone:

```python
TIMEZONE_OFFSET = "+11:00"  # Australia/Melbourne (AEDT)
```

### System Prompt

The agent's behavior is defined in `agent/nova_sonic_bridge.py`. Key features:
- Conversational, phone-optimized responses (2-3 sentences max)
- Confirms important details by repeating them back
- Provides verbal updates when using tools
- Doesn't read URLs over the phone

## Tools

### Calendar Tools
- `create_calendar_event` - Create new events
- `list_calendar_events` - List upcoming events
- `update_calendar_event` - Modify existing events
- `delete_calendar_event` - Remove events

### Notes Tools
- `read_notes` - Read notes for a specific date (defaults to today)
- `update_notes` - Add timestamped notes for a date

Notes are stored in a `my_notes` folder in Google Drive, with one document per day named `YYYY-MM-DD`.

### Other Tools
- `internet_search` - Search the web using Perplexity
- `get_current_datetime` - Get current date/time with timezone

## Usage Examples

**Calendar:**
- "What's on my calendar today?"
- "Schedule a meeting tomorrow at 2pm"
- "Cancel my 3pm appointment"

**Notes:**
- "Add to my notes: remember to buy milk"
- "What did I write yesterday?"
- "Read my notes from December 10th"

**Search:**
- "What's the weather like today?"
- "Search for the latest news on AI"

## Development

### Project Structure

```
agent/
  ├── nova_sonic_bridge.py    # Main agent logic
  ├── server.py               # WebSocket server
  ├── config.py               # Configuration
  ├── aws_secrets.py          # Secrets management
  └── tools/
      ├── google_calendar.py  # Calendar operations
      ├── notes.py            # Notes operations
      ├── internet_search.py  # Web search
      └── datetime_info.py    # Date/time utilities

tests/
  ├── test_calendar.py        # Calendar tool tests
  └── test_notes.py           # Notes tool tests

setup/
  └── tools/google/
      └── authorize_google.py # Google OAuth setup
```

### Adding New Tools

1. Create tool file in `agent/tools/`
2. Define async function for tool logic
3. Add tool definition with JSON schema
4. Register in `agent/tools/__init__.py`

Example:

```python
async def my_tool(params):
    """Tool implementation"""
    return {"result": "success"}

def get_tool_definitions():
    return [{
        "toolSpec": {
            "name": "my_tool",
            "description": "What the tool does",
            "inputSchema": {
                "json": json.dumps({
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    }
                })
            }
        }
    }]
```


## Troubleshooting

**"Invalid scope" error:**
- Regenerate `token.json` with updated scopes in `authorize_google.py`

**Calendar/Notes not working:**
- Verify Google APIs are enabled in Cloud Console
- Check token has correct scopes (calendar, documents, drive.file)
- Update secret in AWS Secrets Manager

**Timezone issues:**
- Update `TIMEZONE_OFFSET` in `config.py`
- Restart agent after changes

## Roadmap

### Planned Features

- **AgentCore Memory Integration**: Persistent conversation memory across calls using Amazon Bedrock AgentCore Memory
- **Async Tool Calls**: Avoid that awkward slience during a tool call like internet search
- **Multi-User Support**: Currently single-user only. Add user identification via phone number to support multiple users with separate calendars and notes

## License

This project is licensed under the MIT-0 License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

## Support

For issues or questions, open a GitHub issue.
