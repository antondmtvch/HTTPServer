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
    OK = 200
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405


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
