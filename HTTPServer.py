import datetime
import socket

from enum import IntEnum
from collections import defaultdict


class Request:
    def __init__(self, http_version: str, method: str, path: str, headers: dict):
        self.http_version = http_version
        self.method = method
        self.path = path
        self.headers = headers


class Response:
    def __init__(self, status: HTTPStatus, headers: dict, body: str = None):
        self.status = status
        self.headers = headers
        self.body = body


class ServerConnectionError(Exception):
    pass


class HTTPRequestError(Exception):
    pass


class TCPServer:
    socket_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    backlog = 10

    def __init__(self, host, port, socket_timeout):
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout
        self.socket = None

    def close_connection(self):
        self.socket.close()
        self.socket = None

    def activate(self):
        if self.socket:
            self.close_connection()
        try:
            self.socket = socket.socket(self.socket_family, self.socket_type)
            self.socket.settimeout(self.socket_timeout)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.backlog)
        except socket.error as err:
            raise ServerConnectionError(err)

    def accept_client_connection(self):
        return self.socket.accept()


class HTTPServer(TCPServer):
    server_name = 'HTTPServer/1.0'

    def __init__(self, host, port, socket_timeout):
        super().__init__(host, port, socket_timeout)
        self.handler = HTTPHandler

    def serve_forever(self):
        super().activate()
        while True:
            client_socket, client_addr = self.accept_client_connection()

    def serve_client(self):
        pass

    def request_parser(self):
        pass

    def headers_parser(self):
        pass

    def send_response(self):
        pass


class HTTPHandler:
    allowed_methods = {'GET', 'HEAD'}
    request_line_max_length = 1024 * 60
    max_headers = 100

    def __init__(self, client_socket):
        self.sock = client_socket
        self.rfile = client_socket.makefile('rb')
        self.wfile = client_socket.makefile('wb')

    def parse_request(self):
        request = self.request_parser()
        headers = self.headers_parser()
        request.headers.update(headers)

    def request_parser(self):
        line = self.rfile.readline(self.request_line_max_length + 1)
        self.__check_line(line)
        try:
            method, path, version = line.strip().split()
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST)
            raise HTTPRequestError()
        if method not in self.allowed_methods:
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
            raise HTTPRequestError()
        return Request(version, path, method, {})

    def headers_parser(self):
        headers = {}
        while True:
            raw = self.rfile.readline(self.MAX_LINE + 1)
            line = str(raw, self.ENCODING).strip()
            if len(line) > self.MAX_LINE:
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if line in {'\r\n', '\n', ''}:
                break
            header = [i.strip() for i in line.split(':', 1)]
            if len(header) != 2:
                self.send_error(HTTPStatus.BAD_REQUEST, f'Bad request syntax {line}')
                return
            key, value = header
            headers[key].add(value)
            if len(headers) > self.MAX_HEADERS:
                self.send_error(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)
                return
        return headers

    def send_response(self, response: Response):
        status_line = f'HTTP/1.1 {response.status.value} {response.status.phrase}\r\n'
        self.wfile.write(status_line.encode(self.ENCODING))

        if response.headers:
            for key, value in response.headers.items():
                header_line = f'{key}: {value}\r\n'.encode(self.ENCODING)
                self.wfile.write(header_line)
        self.wfile(b'\r\n')

        if response.body:
            self.wfile.write(response.body)
        self.wfile.flush()
        self.wfile.close()

    def send_error(self, status, body=None):
        headers = {
            'Date': datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Server': HTTPServer.server_name,
            'Content-Length': '',
            'Content-Type': 'text/plain',
            'Connection': 'close',
        }
        if body:
            body = body.encode(self.ENCODING)
            headers.update({'Content-Length': f'{len(body)}'})
        response = Response(status=status, headers={}, body=body)
        self.send_response(response)
