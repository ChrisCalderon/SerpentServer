import argparse
from . import server
import os
import time
import sys


def filepath(p: str) -> str:
    if not os.path.isfile(p):
        raise argparse.ArgumentTypeError('not a file!')
    return os.path.realpath(p)


def dirpath(p: str) -> str:
    if not os.path.isdir(p):
        raise argparse.ArgumentTypeError('not a directory!')
    return os.path.realpath(p)


def portnum(p: str) -> int:
    try:
        port = int(p)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('not an int!') from exc

    if 0 < port < 65536:
        return port
    else:
        raise argparse.ArgumentTypeError('not a valid port!')


def main():
    parser = argparse.ArgumentParser(
        prog='serpentrpc',
        description='A JSONRPC server with a serpent compiler API.')
    secure = parser.add_mutually_exclusive_group(required=True)
    secure.add_argument('--http', help='Start an HTTP server.',
                        action='store_true', default=False)
    secure.add_argument('--https', help='Start an HTTPS server',
                        action='store_true', default=False)
    parser.add_argument('--certfile', help='Certificate for HTTPS',
                        type=filepath)
    parser.add_argument('--keyfile', help='Private key for HTTPS',
                        type=filepath)
    parser.add_argument('--host', help='Hostname to bind server to')
    parser.add_argument('--port', help='Port to bind server to',
                        type=portnum)
    parser.add_argument('--serverdir', help='Directory to start server in',
                        type=dirpath)

    args = parser.parse_args()  # type: argparse.Namespace
    if args.host is None:
        args.host = '127.0.0.1'

    if args.http:
        if args.port is None:
            args.port = 80
        rpc = server.ThreadedServer((args.host, args.port),
                                    server.JSONRPCHandler)
    else:
        if args.port is None:
            args.port = 443
        if args.certfile is None:
            raise argparse.ArgumentError('certfile required with --https')
        if args.keyfile is None:
            raise argparse.ArgumentError('keyfile required with --https')
        rpc = server.SecureServer(args.certfile,
                                  args.keyfile,
                                  (args.host, args.port),
                                  server.JSONRPCHandler)
    print('starting server')
    rpc.serve_forever()
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('server shutdown')
        rpc.shutdown()

    return 0

if __name__ == '__main__':
    sys.exit(main())