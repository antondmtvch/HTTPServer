import argparse
import datetime
import logging
import os
import socket
import sys
import threading
from collections import namedtuple
from http import HTTPStatus
from urllib.parse import urlparse, unquote

__version__ = '1.0'

DOCUMENT_ROOT = ''
CONTENT_TYPES = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'swf': 'application/x-shockwave-flash',
}

Request = namedtuple('Request', ('method', 'path', 'proto', 'headers'))
Response = namedtuple('Response', ('status', 'body', 'headers'))


class ServerConnectionError(Exception):
    pass


class TCPServer:
    socket_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    backlog = 10

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = None

    def close_serv_connection(self):
        self.socket.close()

    def activate(self):
        if self.socket:
            self.close_serv_connection()
        try:
            self.socket = socket.socket(self.socket_family, self.socket_type)
            self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.backlog)
        except socket.error as err:
            raise ServerConnectionError(err)

    def accept_client_connection(self):
        return self.socket.accept()


class HTTPServer(TCPServer):
    server_name = 'HTTPServer/' + __version__

    def __init__(self, host: str, port: int, workers: int):
        super().__init__(host, port)
        self.workers = workers
        self.handler = MainHTTPHandler

    def handle_requests(self):
        while True:
            client_socket, client_addr = self.accept_client_connection()
            logging.debug(f'{threading.current_thread().name}: {client_addr}')
            self.handler(client_socket)

    def serve_forever(self):
        super().activate()
        for i in range(self.workers):
            thread = threading.Thread(target=self.handle_requests)
            thread.daemon = True
            thread.start()
        logging.info(f'HTTP server run on {self.host}:{self.port}')
        try:
            while True:
                pass
        except KeyboardInterrupt:
            self.close_serv_connection()
            logging.info('Server is stopping.')


class BaseHTTPHandler:
    ALLOWED_METHODS = {'GET', 'HEAD'}
    MAX_LINE = 1024 * 64
    MAX_HEADERS = 100
    ENCODING = 'iso-8859-1'

    def __init__(self, client_socket: socket.socket):
        self.headers_buffer = []
        self.sock = client_socket
        self.rfile = client_socket.makefile('rb')
        self.wfile = client_socket.makefile('wb')
        self.process_request()

    def process_request(self):
        request = self.parse_requestline()
        headers = self.parse_headers()
        if request:
            request.headers.extend(headers)
            handler = 'process_' + request.method
            if not hasattr(self, handler):
                self.send_error(HTTPStatus.NOT_IMPLEMENTED)
            else:
                method_handler = getattr(self, handler)
                method_handler(request)
        self.rfile.close()

    def parse_requestline(self):
        raw = self.rfile.readline(self.MAX_LINE + 1)
        requestline = str(raw, self.ENCODING).strip()
        if len(requestline) > self.MAX_LINE:
            self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
            return
        tokens = tuple(requestline.split())
        if len(tokens) != 3:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        method, path, proto = tokens
        if method not in self.ALLOWED_METHODS:
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            return
        if not proto.startswith('HTTP'):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        if not path.startswith('/'):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        return Request(method=method, path=path, proto=proto, headers=[])

    def parse_headers(self):
        headers = []
        while True:
            raw = self.rfile.readline(self.MAX_LINE + 1)
            if len(raw) > self.MAX_LINE:
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if raw in {b'\r\n', b'\n', b''}:
                break
            headerline = str(raw, self.ENCODING)
            tokens = tuple([i.strip() for i in headerline.split(':', 1)])
            if len(tokens) != 2:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            key, value = tokens
            headers.append(value)
            if len(headers) > self.MAX_HEADERS:
                self.send_error(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)
                return
        return headers

    def send_response(self, response: Response):
        status_line = f'HTTP/1.1 {response.status.value} {response.status.phrase}\r\n'
        self.wfile.write(status_line.encode(self.ENCODING))
        self._send_headers()
        for line in response.body:
            self.wfile.write(line)
        self.wfile.flush()
        self.wfile.close()
        self.sock.close()

    def send_error(self, status: HTTPStatus):
        response = Response(status=status, body=[], headers=self.headers_buffer)
        self.send_response(response)

    def _append_header(self, key: str, value: str) -> None:
        header = f'{key}: {value}\r\n'.encode(self.ENCODING)
        self.headers_buffer.append(header)

    def _start_headers(self):
        self._append_header('Date', datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'))
        self._append_header('Server', HTTPServer.server_name)
        self._append_header('Connection', 'close')

    def _end_headers(self):
        self.wfile.write(b'\r\n')

    def _send_headers(self):
        self._start_headers()
        for header in self.headers_buffer:
            self.wfile.write(header)
        self._end_headers()


class MainHTTPHandler(BaseHTTPHandler):
    def process_HEAD(self, request: Request):
        if document := self.open_document(request.path):
            try:
                response = Response(status=HTTPStatus.OK, body=[], headers=self.headers_buffer)
                self.send_response(response)
            finally:
                document.close()

    def process_GET(self, request: Request):
        if document := self.open_document(request.path):
            try:
                body = (i for i in document)
                response = Response(status=HTTPStatus.OK, body=body, headers=self.headers_buffer)
                self.send_response(response)
            finally:
                document.close()

    def open_document(self, path):
        u = urlparse(unquote(path))
        if u.path == '/':
            path = os.path.join(DOCUMENT_ROOT, 'index.html')
        elif u.path.endswith('/'):
            paths = u.path.split('/')
            path = os.path.join(DOCUMENT_ROOT, *paths, 'index.html')
        else:
            paths = u.path.split('/')
            path = os.path.join(DOCUMENT_ROOT, *paths)
        if not os.path.exists(path):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if os.path.isfile(path):
            ext = path.split('.')[-1]
            ctype = CONTENT_TYPES.get(ext, 'application/octet-stream')
            self._append_header('Content-Type', ctype)
        elif os.path.isdir(path):
            self._append_header('Content-Type', 'text/html')
        file = open(path, 'rb')
        fs = os.fstat(file.fileno())
        self._append_header('Content-Length', str(fs[6]))
        return file


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--documentroot', type=str, required=True)
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('-w', '--workers', type=int, default=15)
    parser.add_argument('--host', type=str, default='localhost')
    return parser.parse_args()


def main():
    args = parse_arguments()
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if not os.path.exists(args.documentroot):
        logging.error(f'Path not exists {args.documentroot}')
        sys.exit(1)
    global DOCUMENT_ROOT
    DOCUMENT_ROOT = args.documentroot
    server = HTTPServer(args.host, args.port, args.workers)
    server.serve_forever()


if __name__ == '__main__':
    main()
