# Discord OAuth Configuration

## Setup Discord Bot & OAuth

### Step 1: Create Discord Application

1. Go to https://discord.com/developers/applications
2. Click **"New Application"**
3. Give it a name: `2K Vision Hub`
4. Go to **OAuth2** section
5. Copy your **Client ID** and **Client Secret**

### Step 2: Set Redirect URL

1. Click **"Add Redirect"**
2. Add: `http://localhost:3000/callback`

### Step 3: Get OAuth Token

```bash
# Users authenticate and get a token to paste in the app
# The token is used to verify Discord membership and roles
```

### Step 4: Role-Based Access Control

Create a Discord server role called `2K Vision Hub Access`

In your Discord server:
1. Create a new role: **Settings → Roles → Create Role**
2. Name it: `2K Vision Hub Access`
3. Give users this role who should have access
4. The app will verify users have this role

---

## How Discord Auth Works

1. **User opens app** → Discord login dialog appears
2. **User authenticates** → Gets OAuth token
3. **App verifies token** → Checks Discord membership
4. **App checks role** → Confirms user has required role
5. **Access granted/denied** → Based on role status

---

## Required Dependencies

```bash
pip install requests
```

---

## Testing

To test Discord authentication without a full Discord server:

```python
# Create a test token
test_token = "YOUR_DISCORD_TOKEN_HERE"

# The app will verify it works
```

---

## Production Deployment

For production, use proper OAuth2 flow:

```python
# Web-based authentication
# Users click "Login with Discord"
# Redirect to Discord OAuth page
# Return with authenticated token
```

---

## Security Notes

⚠️ **Never share your Discord token!**
⚠️ **Keep Client Secret private!**
⚠️ **Use environment variables in production**

```bash
# .env file (never commit this)
DISCORD_TOKEN=your_token_here
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_secret
```

Then load:

```python
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
```

---

## Troubleshooting

**"Authentication failed"**
- Check token is valid
- Make sure user is in the server
- Verify role is assigned

**"Timeout error"**
- Check internet connection
- Discord servers might be down
- Try again in a few seconds

---

For more info: https://discord.com/developers/docs/intro
