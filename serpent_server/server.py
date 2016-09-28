from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import socket
import json
import serpent
import codecs
from collections import namedtuple

RPCError = namedtuple('RPCError', 'json code')
PARSE_ERROR = RPCError(
    json={'code': -32700, 'message': 'Parse error'},
    code=500)
INVALID_REQUEST = RPCError(
    json={'code': -32600, 'message': 'Invalid Request'},
    code=400)
METHOD_NOT_FOUND = RPCError(
    json={'code': -32601, 'message': 'Method not found'},
    code=404)
INVALID_PARAMS = RPCError(
    json={'code': -32602, 'message': 'Invalid params'},
    code=500)
INTERNAL_ERROR = RPCError(
    json={'code': -32603, 'message': 'Internal error'},
    code=500)
_hex = codecs.getencoder('hex')
MAX_PAYLOAD_SIZE = 1 << 20


class ThreadedServer(ThreadingMixIn, HTTPServer):
    pass


class ProcessJSON(BaseHTTPRequestHandler):

    def do_POST(self):
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
        except (TypeError, ValueError):
            response.update(INVALID_PARAMS.json)
            return self._send_json(INVALID_PARAMS.code, response)

        if method == 'compile':  # convert to hex first
            encoded = _hex(result)

    def _send_json(self, code: int, response: dict):
        encoded = json.dump(response).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
