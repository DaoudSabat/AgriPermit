# Simple FastAPI without complex dependencies
# Save this as: C:\Projects\AgriPermit\apps\api\main.py

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "message": "AgriPermit API",
                "status": "running",
                "version": "1.0.0"
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"status": "healthy"}
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/api/v1/parcels':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "parcels": [
                    {
                        "id": "jer_1001",
                        "address": "רחוב הרצל 1, ירושלים",
                        "zone": "חקלאי",
                        "area_sqm": 1000
                    },
                    {
                        "id": "jer_1002",
                        "address": "שכונת עיר גנים, ירושלים",
                        "zone": "חקלאי פרטי",
                        "area_sqm": 1500
                    }
                ]
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/docs':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>AgriPermit API</title>
                <style>
                    body { font-family: Arial; padding: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                    h1 { color: #2e7d32; }
                    .endpoint { background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #2e7d32; }
                    code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🌾 AgriPermit API</h1>
                    <p>Agricultural Land Permit System - API Documentation</p>
                    
                    <h2>Available Endpoints:</h2>
                    
                    <div class="endpoint">
                        <h3>GET /</h3>
                        <p>API status and information</p>
                        <code>curl http://localhost:8000/</code>
                    </div>
                    
                    <div class="endpoint">
                        <h3>GET /health</h3>
                        <p>Health check endpoint</p>
                        <code>curl http://localhost:8000/health</code>
                    </div>
                    
                    <div class="endpoint">
                        <h3>GET /api/v1/parcels</h3>
                        <p>Get list of agricultural parcels</p>
                        <code>curl http://localhost:8000/api/v1/parcels</code>
                    </div>
                    
                    <h2>Status: ✅ Running</h2>
                    <p>Server is operational and ready to accept requests.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[API] {args[0]}")

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, SimpleAPIHandler)
    print('╔═══════════════════════════════════════╗')
    print('║   🌾 AgriPermit API Server          ║')
    print('║                                      ║')
    print('║   Running on: http://localhost:8000  ║')
    print('║   Docs: http://localhost:8000/docs   ║')
    print('║                                      ║')
    print('║   Press Ctrl+C to stop               ║')
    print('╚═══════════════════════════════════════╝')
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down server...')
        httpd.shutdown()