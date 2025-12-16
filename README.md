# Nova Sonic 2 Telephony Agent

A voice-based personal assistant powered by Amazon Nova Sonic 2, capable of managing calendars, taking notes, and searching the internet over phone calls.

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
agentcore configure -e server.py
```

Keep everything default

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

Deploy the API Gateway and Lambda functions to handle phone calls:

```bash
# Install CDK CLI if not already installed
npm install -g aws-cdk

# Install infrastructure dependencies
cd infrastructure
pip install -r requirements.txt

# Deploy with your Runtime ARN from step 4
export RUNTIME_ARN="arn:aws:bedrock:us-east-1:123456789012:agent-runtime/your_runtime_id"
export VONAGE_SIGNATURE_SECRET="your_signature_secret"  # Get from Vonage dashboard
./deploy.sh
```

This deploys:
- API Gateway with `/answer` and `/event` endpoints
- Lambda functions to handle Vonage webhooks
- IAM roles with necessary permissions

**Configure Vonage:**
After deployment, configure your Vonage application with the output URLs:
- Answer URL: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/answer`
- Event URL: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/event`

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

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

## Support

For issues or questions, open a GitHub issue.
