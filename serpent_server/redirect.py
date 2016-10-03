from http.server import BaseHTTPRequestHandler
import urllib.parse


class RedirectHandler(BaseHTTPRequestHandler):
    """A class which handles redirection from http to https."""
    def _get_host(self) -> str:
        parsed = urllib.parse.urlparse(self.headers['HOST'])
        return parsed.netloc + parsed.path

    def _send_error_message(self, code: int) -> bytes:
        message, explain = self.responses[code]
        error_message = self.error_message_format % {'code': code,
                                                     'message': message,
                                                     'explain': explain}
        encoded = error_message.encode('utf8', 'replace')
        self.send_header('Content-Type', self.error_content_type)
        self.send_header('Content-Length', len(encoded))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error_headers(self, code: int):
        self.send_response(code)
        self.send_header('Location', 'https://' + self._get_host())
        self.send_header('Connection', 'close')

    def do_POST(self):
        self._send_error_headers(307)
        self._send_error_message(307)

    def do_HEAD(self):
        self._send_error_headers(301)
        self.end_headers()

    def do_GET(self):
        self._send_error_headers(301)
        self._send_error_message(301)
