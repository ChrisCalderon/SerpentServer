import http.client
import urllib.parse
import json
import os
import codecs
from typing import Callable, Tuple
import types
import threading

_hex = codecs.getencoder('hex') # type: Callable[[bytes], Tuple[bytes, int]]


def _rand() -> str:
    return _hex(os.urandom(4))[0].decode()


class Connection:
    _proxy_lock = threading.Lock()

    def __init__(self, address: str):
        parsed = urllib.parse.urlparse(address)
        if parsed.scheme == 'https':
            self._conn = http.client.HTTPSConnection(parsed.netloc)
        elif parsed.scheme == 'http':
            self._conn = http.client.HTTPConnection(parsed.netloc)
        else:
            raise ValueError('address isn\'t http or https: {}'.format(parsed))
        self._conn.connect()

    def __getattr__(self, item: str):
        with self._proxy_lock:
            # proxy might be created while waiting for lock.
            if hasattr(self, item):
                return getattr(self, item)

            def proxy(self: Connection, *args, **kwds):
                rpc = {'jsonrpc': '2.0', 'method': item, 'id': _rand()}

                if args and not kwds:
                    rpc['params'] = args
                elif kwds and not args:
                    rpc['params'] = kwds
                else:
                    raise ValueError('JSONRPC must be either kwds or args not both')

                encoded = json.dumps(rpc).encode()
                self._conn.request('POST',
                                   '/api',
                                   body=encoded,
                                   headers={'Content-Type': 'application/json'})
                response = self._conn.getresponse()
                return json.loads(response.read().decode())

            doc = '''Proxy method for '{}' RPC method.'''.format(item)
            proxy.__name__ = item
            setattr(Connection, item, proxy)
            return getattr(self, item)
