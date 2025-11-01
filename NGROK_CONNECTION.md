# How ngrok.yml is Connected to Docker Compose

## Connection Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Compose Network (auto-created)                      │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   ngrok      │──────▶│   gateway    │──────▶│  worker   │ │
│  │  container   │      │  container   │      │ container │ │
│  │              │      │              │      │           │ │
│  │ Port 4040    │      │ Port 3000    │      │ Port 8080 │ │
│  │ (web UI)     │      │ (Flask app)  │      │ (Lambda)  │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│       ▲                        ▲                            │
│       │                        │                            │
│       │                        │                            │
│  /etc/ngrok.yml          local_gateway.py                  │
│  (mounted from           (mounted from                      │
│   ./ngrok.yml)           ./local_gateway.py)               │
└─────────────────────────────────────────────────────────────┘
       │
       │ Public HTTPS URL (e.g., https://abc123.ngrok-free.app)
       │
       ▼
   Slack Webhooks
```

## Key Connection Points

### 1. **Volume Mount** (Line 64 in docker-compose.yml)
```yaml
volumes:
  - ./ngrok.yml:/etc/ngrok.yml:ro
```
- **Local file**: `./ngrok.yml` (in your project directory)
- **Container path**: `/etc/ngrok.yml` (where ngrok expects config)
- **Read-only**: `:ro` prevents container from modifying the file

### 2. **Config Flag** (Line 61-62 in docker-compose.yml)
```yaml
command:
  - "start"
  - "--all"
  - "--config"
  - "/etc/ngrok.yml"
```
- Tells ngrok to read configuration from `/etc/ngrok.yml`
- `--all` starts all tunnels defined in the config

### 3. **Service Name Resolution** (Line 8 in ngrok.yml)
```yaml
addr: gateway:3000
```
- `gateway` is the **Docker service name** from docker-compose.yml
- Docker Compose automatically creates DNS entries for service names
- `gateway:3000` resolves to the gateway container's port 3000
- Both services are on the same Docker network, so they can communicate

### 4. **Network Dependencies** (Line 65-66 in docker-compose.yml)
```yaml
depends_on:
  - gateway
```
- Ensures gateway starts before ngrok
- Both services are automatically on the same Docker network

## How It Works Step-by-Step

1. **Docker Compose starts**:
   - Creates a default network for all services
   - Each service gets DNS resolution (e.g., `gateway` resolves to gateway container IP)

2. **Ngrok container starts**:
   - Mounts `./ngrok.yml` → `/etc/ngrok.yml` inside container
   - Reads authtoken and tunnel configuration
   - Starts tunnel to `gateway:3000` (uses Docker DNS to find gateway)

3. **Ngrok creates public URL**:
   - Creates HTTPS URL like `https://abc123.ngrok-free.app`
   - Forwards all traffic from this URL to `gateway:3000`

4. **Traffic flow**:
   - Slack → `https://abc123.ngrok-free.app/slack/events`
   - Ngrok → `gateway:3000/slack/events` (via Docker network)
   - Gateway → `worker:8080` (Lambda invocation)
   - Lambda processes and responds

## Important Notes

- **Same Network**: All services automatically share the same Docker network, enabling service name resolution
- **Service Names**: Use service names (like `gateway`) not `localhost` in ngrok.yml
- **Port Mapping**: 
  - External port 9000 maps to Lambda's internal 8080
  - External port 3000 maps to gateway's internal 3000
  - Ngrok connects to internal Docker network, so it uses `gateway:3000` (not `localhost:3000`)

## Troubleshooting

If ngrok can't reach gateway:
1. Check both services are running: `docker-compose ps`
2. Check ngrok logs: `docker-compose logs ngrok`
3. Verify gateway is up: `docker-compose logs gateway`
4. Test DNS resolution: `docker-compose exec ngrok ping gateway`

