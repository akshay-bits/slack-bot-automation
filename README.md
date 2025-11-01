# AI Automation Slack Bot

This project connects Slack webhooks to AWS Lambda functions for AI-powered automation.

## Setup for Local Development with Slack

Slack requires a **publicly accessible HTTPS URL** for webhooks. Since `localhost:9000` is not accessible from the internet, you need to use a tunneling service like ngrok.

**Recommended Approach:** Use ngrok locally with your Python gateway (no Docker needed for gateway).

### Option 1: Using Ngrok Locally (Simplest - Recommended)

This is the easiest way to get started without dealing with Docker setup for the gateway:

1. **Install ngrok:**
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   # Sign up for free at https://dashboard.ngrok.com/signup
   ```

2. **Start your local gateway:**
   ```bash
   # Make sure you have your .env file with SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET
   python slack_test.py
   ```
   This will start the FastAPI gateway on port 8000.

3. **In a new terminal, start ngrok:**
   ```bash
   ngrok http 8000
   ```

4. **Copy the HTTPS URL:**
   - Ngrok will display a URL like: `https://abc123.ngrok-free.app`
   - Copy this URL and add `/slack/events` to it: `https://abc123.ngrok-free.app/slack/events`

5. **Configure Slack:**
   - Go to your Slack App settings: https://api.slack.com/apps
   - Navigate to "Event Subscriptions"
   - Set Request URL to: `https://abc123.ngrok-free.app/slack/events`
   - Slack will verify the URL automatically

### Option 2: Using Docker Compose with Ngrok (Full Docker Setup)

This setup runs everything in Docker:
- **worker**: Lambda function (port 9000 exposed, 8080 inside container)
- **gateway**: Flask gateway that receives Slack webhooks and forwards to Lambda (port 3000)
- **ngrok**: Tunnels gateway to public HTTPS URL for Slack

**Setup steps:**

1. **Get your ngrok authtoken:**
   - Sign up at https://dashboard.ngrok.com/signup (free)
   - Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken

2. **Add authtoken to ngrok.yml:**
   ```yaml
   authtoken: YOUR_NGROK_AUTHTOKEN_HERE
   ```

3. **Start all services:**
   ```bash
   docker-compose up
   ```

4. **Get your public URL:**
   - Visit http://localhost:4040 to see the ngrok web interface
   - Or check logs: `docker-compose logs ngrok`
   - Look for the HTTPS URL like: `https://abc123.ngrok-free.app`

5. **Configure Slack:**
   - Go to your Slack App settings: https://api.slack.com/apps
   - Navigate to "Event Subscriptions"
   - Set Request URL to: `https://abc123.ngrok-free.app/slack/events`
   - Slack will verify the URL automatically

**Flow:** Slack → Ngrok (public HTTPS) → Gateway (port 3000) → Lambda Worker (port 8080/9000)


### Important Notes

- **Ngrok free tier:** The URL changes every time you restart ngrok (unless you have a paid plan). You'll need to update the Slack webhook URL each time.
- **Ngrok paid plans:** Allow you to use a static domain that doesn't change.
- **Security:** Make sure your `SLACK_SIGNING_SECRET` is set correctly in your `.env` file for signature verification.

## Docker Compose Services

- **worker**: Lambda function container (port 9000)
- **gateway**: FastAPI gateway for Slack webhooks (port 8000)
- **ngrok**: Tunnel service exposing gateway publicly (web UI on port 4040)

## Environment Variables

Required variables in `.env`:
- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_SIGNING_SECRET`: Your Slack app signing secret
- `SLACK_CHANNEL_ID`: Default Slack channel
- `SPREADSHEET_ID`: Google Sheets ID
- `ANTHROPIC_API_KEY`: Anthropic API key

