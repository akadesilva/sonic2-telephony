# Google OAuth2 Setup

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the following APIs:
   - Google Calendar API
   - Google Docs API
   - Google Sheets API

## Step 2: Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Configure OAuth consent screen (if prompted):
   - User Type: External
   - App name: "Personal Assistant"
   - Add your email as test user
4. Application type: **Desktop app**
5. Name: "Personal Assistant Desktop"
6. Click **Create**
7. Download the JSON file
8. Save it as `credentials.json` in the `agent/` folder

## Step 3: Authorize (One-Time)

```bash
cd agent
python3 authorize_google.py
```

This will:
- Open your browser
- Ask you to login to Google
- Request permissions for Calendar, Docs, Sheets
- Save `token.json` with refresh token

## Step 4: Deploy

The `token.json` file will be automatically included when you deploy:

```bash
agentcore launch
```

## Token Refresh

The token automatically refreshes itself. It won't expire unless you:
- Revoke access in Google Account settings
- Delete the token.json file

## Security Notes

- `credentials.json` and `token.json` are in `.gitignore`
- Never commit these files to git
- The token has access to YOUR Google account only
- Revoke access anytime at: https://myaccount.google.com/permissions

## Testing Tools

Once deployed, you can:

**Calendar:**
- "Create a calendar event for tomorrow at 2pm titled Team Meeting"
- "What's on my calendar today?"

**Docs:**
- "Create a new doc called Meeting Notes"
- "Read the doc with ID abc123"
- "Add 'Action items: ...' to doc abc123"

**Sheets:**
- "Create a new spreadsheet called Budget 2024"
- "Read data from sheet abc123"
- "Add a row with values Name, Email, Phone to sheet abc123"
