from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import ssl
import socket
import json
import serpent
import codecs
from collections import namedtuple
from typing import Callable, Tuple


RPCError = namedtuple('RPCError', 'json code')
PARSE_ERROR = RPCError(
    json={'code': -32700, 'message': 'Parse error'},
    code=500
)
INVALID_REQUEST = RPCError(
    json={'code': -32600, 'message': 'Invalid Request'},
    code=400
)
METHOD_NOT_FOUND = RPCError(
    json={'code': -32601, 'message': 'Method not found'},
    code=404
)
INVALID_PARAMS = RPCError(
    json={'code': -32602, 'message': 'Invalid params'},
    code=500
)
INTERNAL_ERROR = RPCError(
    json={'code': -32603, 'message': 'Internal error'},
    code=500
)
_hex = codecs.getencoder('hex')  # type: Callable[[bytes], Tuple[bytes, int]]
MAX_PAYLOAD_SIZE = 1 << 20


class JSONRPCHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != '/api':
            self.send_error(404)
        content_type = self.headers['Content-Type']
        if content_type == 'application/json':
            self._process_jsonrpc()
        else:
            self.send_error(415)

    def _process_jsonrpc(self):
        length = self.headers['Content-Length']
        if length is None:
            return self.send_error(411)
        length = int(length)
        if length > MAX_PAYLOAD_SIZE:
            return self.send_error(413)

        try:
            payload = self.rfile.read(int(length))  # type: bytes
        except socket.timeout:
            return self.send_error(408)

        response = {'jsonrpc': '2.0', 'id': None}
        try:
            request = json.loads(payload.decode('utf8'))
        except json.JSONDecodeError:
            response.update(PARSE_ERROR.json)
            return self._send_json(PARSE_ERROR.code, response)

        response.update(request.get('id'))

        method = request.get('method')
        params = request.get('params')
        version = request.get('jsonrpc')
        if method is None or params is None or version != '2.0':
            response.update(INVALID_REQUEST.json)
            return self._send_json(INVALID_REQUEST.code, response)

        try:
            serpent_func = getattr(serpent, method)
        except AttributeError:
            response.update(METHOD_NOT_FOUND.json)
            return self._send_json(METHOD_NOT_FOUND.code, response)

        try:
            if isinstance(params, list):
                result = serpent_func(*params)
            elif isinstance(params, dict):
                result = serpent_func(**params)
            else:
                raise TypeError
        except (TypeError, ValueError):
            response.update(INVALID_PARAMS.json)
            return self._send_json(INVALID_PARAMS.code, response)

        if method == 'compile':  # convert to hex first
            result = '0x' + _hex(result)[0].decode()

        response['result'] = result
        self._send_json(200, response)

    def _send_json(self, code: int, response: dict):
        encoded = json.dumps(response).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class ThreadedServer(ThreadingMixIn, HTTPServer):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *args, **kwds):
        self._serve_forever_thread = None  # type: threading.Thread
        super().__init__(*args, **kwds)

    def serve_forever(self, poll_interval=0.5):
        self._serve_forever_thread = threading.Thread(
            target=super().serve_forever,
            args=(poll_interval,)
        )
        self._serve_forever_thread.start()


class SecureServer(ThreadedServer):
    def __init__(self, certfile: str, keyfile: str, *args, **kwds):
        self._certfile = certfile
        self._keyfile = keyfile
        super().__init__(*args, **kwds)

    def server_bind(self):
        super().server_bind()
        self.socket = ssl.wrap_socket(self.socket,
                                      server_side=True,
                                      certfile=self._certfile,
                                      keyfile=self._keyfile,
                                      do_handshake_on_connect=False)

    def get_request(self):
        sock, addr = super().get_request()
        sock.do_handshake()
        return sock, addr
