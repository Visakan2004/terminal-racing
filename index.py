"""
Web entrypoint for Vercel deployment.
Provides both WSGI standard `app` and `BaseHTTPRequestHandler` `handler`.
"""
from http.server import BaseHTTPRequestHandler

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏎️ Terminal Racing - Extreme Combat Edition</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: #0b0c10;
            color: #c5c6c7;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: #1f2833;
            border: 2px solid #66fcf1;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(102, 252, 241, 0.2);
            max-width: 650px;
            width: 100%;
            padding: 35px;
            text-align: center;
        }
        h1 {
            color: #66fcf1;
            font-size: 2rem;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        p {
            margin-bottom: 20px;
            line-height: 1.6;
            color: #c5c6c7;
        }
        .cmd-box {
            background: #0b0c10;
            border: 1px solid #45a29e;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', Courier, monospace;
            color: #45a29e;
            font-weight: bold;
            font-size: 0.95rem;
            word-break: break-all;
            margin: 20px 0;
            user-select: all;
        }
        .btn-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 25px;
        }
        a.btn {
            background: #66fcf1;
            color: #0b0c10;
            text-decoration: none;
            font-weight: bold;
            padding: 12px 24px;
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        a.btn:hover {
            background: #45a29e;
            color: #ffffff;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🏎️ Terminal Racing</h1>
        <p><strong>Extreme Combat Edition</strong> — High-octane ASCII combat racing game featuring weaponized hypercars, twin plasma shooters, turbo boost, and dynamic combat FX.</p>
        
        <div class="cmd-box">
            docker run -it --rm ghcr.io/visakan2004/terminal-racing:latest
        </div>

        <p>Run the single command above in your terminal or Docker environment to play instantly!</p>

        <div class="btn-group">
            <a href="https://github.com/Visakan2004/terminal-racing" class="btn" target="_blank">View GitHub Repo</a>
        </div>
    </div>
</body>
</html>"""

# WSGI standard entrypoint (supported by Vercel Python runtime)
def app(environ, start_response):
    status = '200 OK'
    response_headers = [
        ('Content-type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(HTML_CONTENT.encode('utf-8'))))
    ]
    start_response(status, response_headers)
    return [HTML_CONTENT.encode('utf-8')]

# BaseHTTPRequestHandler entrypoint for backwards compatibility
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode('utf-8'))
