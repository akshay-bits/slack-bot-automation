# Slack Webhook Setup Guide

## Step 1: Get Your Ngrok Public URL

Run the helper script:
```bash
./get_ngrok_url.sh
```

Or get it manually:
```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; print([t['public_url'] for t in json.load(sys.stdin).get('tunnels', [])][0])"
```

Example URL: `https://clearly-migrational-yu.ngrok-free.dev`

## Step 2: Configure Slack App

1. **Go to Slack API Dashboard:**
   - Visit: https://api.slack.com/apps
   - Select your app (or create a new one)

2. **Enable Event Subscriptions:**
   - Click **"Event Subscriptions"** in the left sidebar
   - Toggle **"Enable Events"** to ON

3. **Set Request URL:**
   - **Request URL:** `https://YOUR_NGROK_URL.ngrok-free.dev/slack/events`
   - Example: `https://clearly-migrational-yu.ngrok-free.dev/slack/events`
   - Click **"Save Changes"**
   - Slack will verify the URL automatically (should show ✅ "Verified")

## Step 3: Subscribe to Bot Events

1. Scroll down to **"Subscribe to bot events"**
2. Click **"Add Bot User Event"**
3. Add these events:
   - `app_mention` - When bot is mentioned
   - `message.channels` - Messages in channels (optional)
   - `message.im` - Direct messages (optional)

4. Click **"Save Changes"**

## Step 4: Install App to Workspace

1. Go to **"Install App"** in the left sidebar
2. Click **"Install to Workspace"**
3. Authorize the app

## Step 5: Test Your Bot

1. In Slack, mention your bot: `@YourBotName /generate_pages`
2. Check Docker logs:
   ```bash
   docker-compose logs -f gateway worker
   ```

## Important Notes

### Ngrok URL Changes
- **Free tier**: URL changes each time you restart ngrok
- **After restarting**, you need to update the Slack webhook URL
- Use `./get_ngrok_url.sh` to get the new URL

### Gateway Routes
- The gateway now handles both `/` and `/slack/events`
- Both endpoints will work, but `/slack/events` is recommended

### Environment Variables Required
Make sure your `.env` file has:
- `SLACK_BOT_TOKEN` - Bot User OAuth Token
- `SLACK_SIGNING_SECRET` - App Signing Secret
- `SLACK_CHANNEL_ID` - Default channel ID

## Troubleshooting

### Slack shows "Request URL verification failed"
- Check gateway is running: `docker-compose ps gateway`
- Check gateway logs: `docker-compose logs gateway`
- Verify ngrok URL is accessible: `curl https://YOUR_URL.ngrok-free.dev/slack/events`

### Getting 404 errors
- Make sure you're using `/slack/events` at the end of the URL
- Gateway now handles `/` but `/slack/events` is preferred

### Bot not responding
- Check worker logs: `docker-compose logs worker`
- Verify Lambda is receiving events: `docker-compose logs -f worker`
- Check gateway is forwarding: `docker-compose logs -f gateway`

