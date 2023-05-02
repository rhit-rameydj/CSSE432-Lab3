import socket
import sys
import threading
import traceback
from urllib.parse import urlparse


class BadRequestException(Exception):
    pass


class NotImplementedException(Exception):
    pass


class HttpRequest:
    def __init__(self, request):
        split = request.split()
        self.method = split[0]
        self.url = urlparse(split[1]).netloc

        if ':' in self.url:
            self.url, self.port = self.url.split(':')
            self.port = int(self.port)
        else:
            self.port = 80

        self.http_version = split[2]

    @classmethod
    def verify_valid_http_request(cls, request):
        # Split the request into lines
        lines = request.split('\r\n')

        # The first line should contain the HTTP method, path, and version
        first_line_parts = lines[0].split(' ')
        if len(first_line_parts) != 3:
            raise BadRequestException('First line should contain the HTTP method, path, and version')
        method, path, version = first_line_parts

        if method not in ['GET']:
            raise NotImplementedException(f'Method {method} not supported')

        # The version should be "HTTP/1.0"
        #if version != "HTTP/1.0":
        #    raise NotImplementedException('The proxy only supports HTTP/1.0')

        # Check that all headers have the correct format
        for line in lines[1:]:
            if line == '':
                # An empty line indicates the end of the headers
                break
            if ':' not in line:
                # Headers should be of the form "Header-Name: header value"
                raise BadRequestException('Headers should be in the form \"Header-Name: header value\"')
            header_name, header_value = line.split(':', 1)
            if not header_name.strip() or not header_value.strip():
                # Header names and values should not be empty
                raise BadRequestException('Header names and values should not be empty')

        # The request is valid
        return True


def handle_client(client_socket):
    # Receive data from the client
    try:
        request_bytes = client_socket.recv(4096) + b'\r\n'
        request_bytes = request_bytes.decode().replace('HTTP/1.1', 'HTTP/1.0').replace('\r\nConnection: keep-alive', '').replace('\r\nUpgrade-Insecure-Requests: 1', '').encode()
        print(request_bytes.decode())
        print(request_bytes)
        HttpRequest.verify_valid_http_request(request_bytes.decode())
        request = HttpRequest(request_bytes.decode())
    except BadRequestException:
        print("Handling bad request")
        response = b"HTTP/1.0 500 Malformed Request\r\nContent-Type: text/html\r\n\r\n<html><body><h1>500 Malformed Request</h1></body></html>"
        client_socket.send(response)
        return
    except NotImplementedException:
        print("Handling not implemented")
        response = b"HTTP/1.0 501 Not Implemented\r\nContent-Type: text/html\r\n\r\n<html><body><h1>501 Not Implemented</h1></body></html>"
        client_socket.send(response)
        return
    except:
        traceback.print_exc(file=sys.stderr)
        return

    print(request.__dict__)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.connect((request.url, request.port))
    server_socket.send(request_bytes)

    # Receive data from the server
    response = b''
    while True:
        data = server_socket.recv(4096)
        if not data:
            break
        response += data

    client_socket.sendall(response)

    server_socket.close()


def main():
    # Create a listening socket
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(("localhost", 8080))
    proxy_socket.listen(5)

    while True:
        # Accept a client connection
        client_socket, client_address = proxy_socket.accept()
        print("connected")

        # Create a new thread to handle the client request
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()


if __name__ == '__main__':
    main()
