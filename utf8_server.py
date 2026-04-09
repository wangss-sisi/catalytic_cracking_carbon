import http.server
import socketserver

PORT = 5003

class UTF8HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        if path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(path, 'rb') as f:
                return f
        else:
            return super().send_head()

with socketserver.TCPServer(('', PORT), UTF8HTTPRequestHandler) as httpd:
    print(f'Server running at http://localhost:{PORT}')
    httpd.serve_forever()