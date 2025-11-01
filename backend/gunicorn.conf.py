import os

# Use Railway's PORT environment variable, fallback to 8000 for local dev
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
