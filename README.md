# Log Watcher - Real-time Log Viewer

A real-time log watching solution (like `tail -f`) for web browsers.

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
