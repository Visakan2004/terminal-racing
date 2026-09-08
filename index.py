"""
Web entrypoint for Vercel deployment.
Serves the complete playable Terminal Racing Web Arcade Game directly in browser.
"""
import os
from http.server import BaseHTTPRequestHandler

HTML_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

def get_html_content() -> bytes:
    try:
        if os.path.exists(HTML_FILE_PATH):
            with open(HTML_FILE_PATH, "rb") as f:
                return f.read()
    except Exception:
        pass
    return b"<h1>Terminal Racing Web Game</h1>"

# Standard WSGI app entrypoint for Vercel Python runtime
def app(environ, start_response):
    content = get_html_content()
    status = '200 OK'
    response_headers = [
        ('Content-type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(content))),
        ('Cache-Control', 'public, max-age=0, must-revalidate')
    ]
    start_response(status, response_headers)
    return [content]

# BaseHTTPRequestHandler entrypoint for backward compatibility
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = get_html_content()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)
