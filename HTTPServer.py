import socket

from enum import IntEnum
from collections import defaultdict


class Request:
    def __init__(self, http_version, method, path, headers):
        self.http_version = http_version
        self.method = method
        self.path = path
        self.headers = headers if headers else {}


class Response:
    def __init__(self):
        pass


class HTTPStatus(IntEnum):
    def __new__(cls, value, phrase):
        obj = int.__new__(cls)
        obj._value_ = value
        obj.phrase = phrase
        return obj

    OK = 200, 'OK'
    BAD_REQUEST = 400, 'Bad Request'
    FORBIDDEN = 403, 'Forbidden'
    NOT_FOUND = 404, 'Not Found'
    METHOD_NOT_ALLOWED = 405, 'Method Not Allowed'
    UNSUPPORTED_MEDIA_TYPE = 415, 'Unsupported Media Type'


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
    def __init__(self, host, port, socket_timeout):
        super().__init__(host, port, socket_timeout)

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
        header_count = 0
        headers = defaultdict(set)
        while True:
            header_count += 1
            line = self.rfile.readline(self.request_line_max_length + 1)
            self.__check_line(line)
            if line in (b'\r\n', b'\n', b''):
                break
            try:
                header, value = line.strip().split(' :', 1)
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                raise HTTPRequestError()
            headers[header].add(value)
            if header_count > self.max_headers:
                self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
                raise HTTPRequestError()
        return headers

    def __check_line(self, line):
        if len(line) > self.request_line_max_length:
            self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            raise HTTPRequestError()

    def send_response(self, response):
        self.wfile.writelines(response)

    def send_error(self, status):
        response = f'HTTP/1.1 {status.value} {status.phrase}'.encode('iso-8859-1')
        self.send_response(response)
