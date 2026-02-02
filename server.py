#!/usr/bin/env python3
"""Log Watcher - Fixed Version with Queue-based Broadcasting"""

import os, json, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue, Empty

# Config
LOG_FILE = os.environ.get('LOG_FILE', './sample.log')
PORT = 8080

# State - use queues for thread-safe communication
client_queues = []  # List of Queue objects, one per client
clients_lock = threading.Lock()
last_position = 0


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def get_last_n_lines(filepath, n=10):
    """Reverse read for large files"""
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    
    lines, position, partial = [], os.path.getsize(filepath), ''
    with open(filepath, 'rb') as f:
        while position > 0 and len(lines) < n:
            chunk_size = min(8192, position)
            position -= chunk_size
            f.seek(position)
            chunk = f.read(chunk_size).decode('utf-8', errors='replace') + partial
            parts = chunk.split('\n')
            partial = parts[0]
            for line in reversed(parts[1:]):
                if line.strip():
                    lines.insert(0, line)
                    if len(lines) >= n:
                        break
        if partial.strip() and len(lines) < n:
            lines.insert(0, partial)
    return lines[-n:]


def broadcast(event, data):
    """Send message to all client queues"""
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with clients_lock:
        count = len(client_queues)
        if count > 0:
            log(f"Broadcasting to {count} clients: {data.get('lines', [])[:1]}...")
            for q in client_queues:
                q.put(msg)


def watch_file():
    """Watch file for changes"""
    global last_position
    
    if os.path.exists(LOG_FILE):
        last_position = os.path.getsize(LOG_FILE)
    log(f"Watcher started, position: {last_position}")
    
    while True:
        try:
            if os.path.exists(LOG_FILE):
                size = os.path.getsize(LOG_FILE)
                
                if size < last_position:
                    log("File truncated")
                    last_position = 0
                
                if size > last_position:
                    with open(LOG_FILE, 'r') as f:
                        f.seek(last_position)
                        content = f.read()
                    
                    lines = [l for l in content.split('\n') if l.strip()]
                    log(f"New content: {last_position} -> {size}, lines: {len(lines)}")
                    last_position = size
                    
                    if lines:
                        broadcast('update', {'lines': lines})
        except Exception as e:
            log(f"Watcher error: {e}")
        
        time.sleep(0.1)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    
    def log_message(self, *a): pass
    
    def do_GET(self):
        if self.path in ('/', '/log'):
            self.serve_html()
        elif self.path == '/events':
            self.serve_sse()
        elif self.path == '/health':
            with clients_lock:
                self.send_json({'status': 'ok', 'clients': len(client_queues), 'pos': last_position})
        else:
            self.send_error(404)
    
    def serve_html(self):
        body = HTML.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def serve_sse(self):
        # Create queue for this client
        my_queue = Queue()
        
        # SSE headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()
        
        # Send initial lines
        lines = get_last_n_lines(LOG_FILE)
        init_msg = f"event: init\ndata: {json.dumps({'lines': lines})}\n\n"
        self.wfile.write(init_msg.encode())
        self.wfile.flush()
        
        # Register this client's queue
        with clients_lock:
            client_queues.append(my_queue)
        log(f"Client connected, total: {len(client_queues)}")
        
        try:
            while True:
                try:
                    # Wait for message with timeout
                    msg = my_queue.get(timeout=15)
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
                    log(f"Sent to client")
                except Empty:
                    # Send heartbeat
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except Exception as e:
            log(f"Client error: {e}")
        finally:
            with clients_lock:
                if my_queue in client_queues:
                    client_queues.remove(my_queue)
            log(f"Client disconnected, total: {len(client_queues)}")
    
    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


HTML = '''<!DOCTYPE html><html><head><title>Log Watcher</title>
<style>body{background:#1a1a2e;color:#eee;font-family:monospace;padding:20px}
#log{background:#0f0f1a;padding:15px;height:85vh;overflow-y:auto;border-radius:8px}
.line{padding:3px 0;border-bottom:1px solid #333}
.new{background:rgba(0,255,100,0.15);animation:fade 3s}
@keyframes fade{from{background:rgba(0,255,100,0.4)}}</style></head>
<body><div id="s">Connecting...</div><div id="log"></div>
<script>
const log=document.getElementById('log'),s=document.getElementById('s');
const es=new EventSource('/events');
es.onopen=()=>{s.textContent='* Connected';console.log('SSE connected')};
es.onerror=(e)=>{s.textContent='* Reconnecting...';console.log('SSE error',e)};
es.addEventListener('init',e=>{
    console.log('init',e.data);
    JSON.parse(e.data).lines.forEach(l=>add(l,false));
});
es.addEventListener('update',e=>{
    console.log('update',e.data);
    JSON.parse(e.data).lines.forEach(l=>add(l,true));
});
function add(t,isNew){
    const d=document.createElement('div');
    d.className='line'+(isNew?' new':'');
    d.textContent=t;
    log.appendChild(d);
    log.scrollTop=log.scrollHeight;
}
</script></body></html>'''


class ThreadedServer(HTTPServer):
    allow_reuse_address = True
    def process_request(self, r, a):
        threading.Thread(target=lambda:self._h(r,a), daemon=True).start()
    def _h(self, r, a):
        try: self.finish_request(r, a)
        finally: self.shutdown_request(r)


if __name__ == '__main__':
    # Fresh log
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    with open(LOG_FILE, 'w') as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] Server started\n")
    
    # Start watcher
    threading.Thread(target=watch_file, daemon=True).start()
    
    log(f"Server on http://localhost:{PORT}/log")
    ThreadedServer(('0.0.0.0', PORT), Handler).serve_forever()
