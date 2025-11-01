import json
import os
import sys
import httpx

# Ensure the local 'src' directory is on sys.path so imports inside
# src/lambda_handler.py like 'from services...' resolve correctly.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(CURRENT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
from flask import Flask, request, make_response
from src.validation import validate_slack_event  # reuse validation (no AWS deps)

app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    try:
        body = request.get_json(force=True, silent=False)
    except Exception:
        return make_response("Invalid JSON", 400)

    # Slack URL verification
    if body.get("type") == "url_verification" and "challenge" in body:
        return make_response(body["challenge"], 200, {"Content-Type": "text/plain"})

    is_valid, msg = validate_slack_event(body)
    if not is_valid:
        return make_response(f"Invalid event: {msg}", 400)

    # For event_callback: forward to worker Lambda container (Lambda RIE)
    if body.get("type") == "event_callback":
        try:
            # Use Docker service name 'worker' when running in Docker, or 'localhost' when running locally
            # Lambda RIE listens on port 8080 inside the container
            worker_host = os.getenv("WORKER_HOST", "worker")  # Default to Docker service name
            worker_port = os.getenv("WORKER_PORT", "8080")     # Lambda RIE port inside container
            invoke_url = f"http://{worker_host}:{worker_port}/2015-03-31/functions/function/invocations"
            print(f"Forwarding to Lambda at: {invoke_url}")
            print("request body: ", body)
            
            with httpx.Client(timeout=30) as client:
                resp = client.post(invoke_url, json=body)
                # Always return 200 to Slack quickly
                if resp.status_code >= 400:
                    print(f"Lambda error: {resp.text}")
                    return make_response(json.dumps({"ok": True, "worker_error": resp.text}), 200)
                print(f"Lambda response: {resp.status_code}")
        except Exception as e:
            print(f"Error forwarding to Lambda: {str(e)}")
            # Still 200 to avoid Slack retries
            return make_response(json.dumps({"ok": True, "worker_error": str(e)}), 200)
        return make_response(json.dumps({"ok": True}), 200)

    return make_response(json.dumps({"error": "Unsupported"}), 400)

@app.route("/", methods=["GET", "POST"])
def root():
    """Handle root path - forward POST requests to slack_events"""
    if request.method == "POST":
        # Forward POST requests to slack_events handler
        return slack_events()
    # GET requests return info
    return make_response(json.dumps({
        "status": "ok",
        "message": "Slack gateway is running",
        "endpoint": "/slack/events",
        "usage": "Configure Slack Event Subscriptions to POST to /slack/events"
    }), 200, {"Content-Type": "application/json"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)