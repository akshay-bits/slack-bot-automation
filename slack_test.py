import os
import json
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()
load_dotenv()

# Initialize Slack app
signing_secret = os.getenv("SLACK_SIGNING_SECRET")
bot_token = os.getenv("SLACK_BOT_TOKEN")

if not signing_secret:
    print("⚠️  WARNING: SLACK_SIGNING_SECRET not set. Signature verification will fail for non-challenge events.")
else:
    print(f"✓ SLACK_SIGNING_SECRET loaded: {signing_secret[:10]}...")

if not bot_token:
    print("⚠️  WARNING: SLACK_BOT_TOKEN not set.")

slack_app = App(
    token=bot_token,
    signing_secret=signing_secret
)
handler = SlackRequestHandler(slack_app)

@slack_app.event("app_mention")
def handle_app_mention(event, say):
    """Handle when bot is mentioned with commands like @bot-name /generate-pages"""
    user = event.get("user")
    text = event.get("text", "")
    channel = event.get("channel")
    ts = event.get("ts")
    
    print(f"📨 App mention received - User: {user}, Text: {text}, Channel: {channel}")
    
    # Remove bot mention from text (format: <@U123456>)
    # Also clean markdown formatting
    clean_text = re.sub(r"<@[^>]+>", "", text).strip()
    clean_text = re.sub(r"[`*_>]", "", clean_text).strip()
    
    if not clean_text:
        say("Hi! I'm ready. Try: `/generate-pages` or `/generate_pages`")
        return
    
    # Split command and arguments
    lines = clean_text.splitlines()
    command_line = lines[0].strip()
    command_parts = command_line.split()
    command = command_parts[0].lower() if command_parts else ""
    
    print(f"🔍 Parsed command: {command}")
    
    # Handle different commands
    if command in ["/generate-pages", "/generate_pages", "generate-pages", "generate_pages"]:
        say("🚀 Generating pages... This may take a moment.", thread_ts=ts)
        # TODO: Call your GeneratePagesWorkflow here
        # For now, just respond
        say("✅ Pages generation completed! (Integration with workflow pending)", thread_ts=ts)
    
    elif command in ["/help", "help"]:
        say("Available commands:\n• `/generate-pages` - Generate pages from spreadsheet\n• `/help` - Show this help")
    
    else:
        say(f"❓ Unknown command: `{command}`\nTry `/help` for available commands", thread_ts=ts)


@slack_app.event("message")
def handle_message(event, say):
    """Handle regular messages (not mentions)"""
    user = event.get("user")
    text = event.get("text")
    channel = event.get("channel")
    
    # Ignore bot messages and messages without text
    if event.get("bot_id") or not text:
        return
    
    print(f"💬 Message received - User: {user}, Text: {text}, Channel: {channel}")
    
    # Only respond if explicitly mentioned or in DM
    # For now, just log regular messages
    pass

@app.post("/slack/events")
@app.post("/")
async def slack_events(request: Request):
    # Read body first to check for URL verification challenge
    # Challenges don't require signature verification
    body_bytes = await request.body()
    
    # Handle URL verification challenge explicitly
    # This bypasses signature verification which isn't needed for challenges
    try:
        if body_bytes:
            body_dict = json.loads(body_bytes.decode())
            if body_dict.get("type") == "url_verification":
                challenge = body_dict.get("challenge")
                if challenge:
                    print(f"✓ URL verification challenge received: {challenge}")
                    return PlainTextResponse(content=challenge)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    
    # For non-challenge events, pass to slack_bolt with reconstructed request
    # Reconstruct request body for signature verification
    _body_sent = [False]  # Use list to work around closure issue
    async def receive():
        if not _body_sent[0]:
            _body_sent[0] = True
            return {"type": "http.request", "body": body_bytes}
        return {"type": "http.request", "body": b""}
    
    # Preserve the original scope (includes headers needed for signature verification)
    scope = request.scope.copy()
    new_request = Request(scope, receive)
    
    # slack_bolt will verify signature and process the event
    try:
        # Debug: print request headers
        print(f"Request headers: {dict(request.headers)}")
        print(f"Body length: {len(body_bytes)} bytes")
        
        response = await handler.handle(new_request)
        return response
    except Exception as e:
        # Log the error for debugging
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"❌ Error from slack_bolt handler: {error_type}: {error_msg}")
        print(f"   Full traceback:", end=" ")
        import traceback
        traceback.print_exc()
        
        # If it's a signature verification error, provide helpful message
        if "signature" in error_msg.lower() or "verification" in error_msg.lower():
            print("\n💡 Signature verification failed. Check:")
            print("   1. SLACK_SIGNING_SECRET matches your app's signing secret")
            print("   2. Headers are being preserved correctly")
            print("   3. Request body hasn't been modified")
        
        # Re-raise to return proper error response
        raise

@app.get("/")
async def root():
    return {"message": "Slack bot is running! Use /slack/events for Slack events."}


@app.get("/health")
async def health():
    return {"status": "ok", "slack_app_configured": slack_app.client.token is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)