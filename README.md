# Log Watcher - Real-time Log Viewer

A real-time log watching solution (like `tail -f`) for web browsers.

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM OVERVIEW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Browser  │     │ Browser  │     │ Browser  │
    │ Client 1 │     │ Client 2 │     │ Client N │
    └────┬─────┘     └────┬─────┘     └────┬─────┘
         │                │                │
         │    SSE         │    SSE         │    SSE
         │  (HTTP/1.1)    │  (HTTP/1.1)    │  (HTTP/1.1)
         │                │                │
         ▼                ▼                ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     HTTP SERVER (Port 8080)                      │
    │  ┌─────────────────────────────────────────────────────────┐    │
    │  │                   Request Router                         │    │
    │  │   GET /      → HTML Page                                │    │
    │  │   GET /events → SSE Stream                              │    │
    │  │   GET /health → Health Check                            │    │
    │  └─────────────────────────────────────────────────────────┘    │
    │                            │                                     │
    │  ┌─────────────────────────┴─────────────────────────────┐      │
    │  │              CLIENT MANAGER                            │      │
    │  │   • Track connected clients                           │      │
    │  │   • Thread-safe client list                           │      │
    │  │   • Broadcast messages to all                         │      │
    │  └───────────────────────────────────────────────────────┘      │
    └─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Broadcast
                                 │
    ┌────────────────────────────┴────────────────────────────────────┐
    │                      FILE WATCHER THREAD                         │
    │  ┌─────────────────────────────────────────────────────────┐    │
    │  │   • Poll file every 100ms                               │    │
    │  │   • Track last_position (file offset)                   │    │
    │  │   • Detect new content: size > last_position            │    │
    │  │   • Read only NEW bytes                                 │    │
    │  │   • Handle log rotation (size < last_position)          │    │
    │  └─────────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Read
                                 ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                        LOG FILE                                  │
    │   ┌─────────────────────────────────────────────────────────┐   │
    │   │  Line 1: [10:00:00] Server started                      │   │
    │   │  Line 2: [10:00:01] Request received                    │   │
    │   │  Line 3: [10:00:02] Processing...                       │   │
    │   │  ...                                                     │   │
    │   │  Line N: [10:05:00] Latest entry    ← last_position     │   │
    │   │  ─────────────────────────────────────────────────────  │   │
    │   │  Line N+1: [10:05:01] NEW entry     ← Read this!        │   │
    │   └─────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Start the server
python3 server.py

# 2. Open in browser
open http://localhost:8080/log

# 3. Generate test logs (in another terminal)
bash test_logs.sh
```

## What You'll See

- **Initial load**: Last 10 lines from the log file
- **Real-time**: New logs appear automatically (green highlight)

## Files

| File | Description |
|------|-------------|
| `server.py` | Main server (218 lines) |
| `test_logs.sh` | Log generator script |
| `sample.log` | Log file being watched |

## Configuration

Edit top of `server.py`:
```python
LOG_FILE = 'sample.log'  # File to watch
PORT = 8080              # Server port
```

## Stop

```bash
pkill -f "python3 server.py"
pkill -f "test_logs.sh"
```

## Key Features

- SSE (Server-Sent Events) for real-time streaming
- Reverse-read algorithm for efficient last N lines
- Position tracking (only sends new content)
- Multi-client support
- No external dependencies (stdlib only)
