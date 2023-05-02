import socket
import sys
import threading
import traceback


class HttpRequest:
    def __init__(self, request):
        split = request.split()
        self.method = split[0]

        if 'http://' in split[1]:
            split[1] = split[1][7:]

        if split[1].endswith('/'):
            split[1] = split[1][:-1]

        if ':' in split[1]:
            self.url, self.port = split[1].split(':')
            self.port = int(self.port)
        else:
            self.url = split[1]
            self.port = 80

        self.http_version = split[2]
        self.headers = self.parse_headers(request)

    def parse_headers(self, request):
        headers = {}
        lines = request.split('\r\n')
        for line in lines[1:]:
            parts = line.split(': ')
            if len(parts) == 2:
                key = parts[0].lower()
                value = parts[1]
                headers[key] = value
        return headers

    @classmethod
    def is_valid_http_request(cls, request):
        # Split the request into lines
        lines = request.split('\r\n')

        # The first line should contain the HTTP method, path, and version
        first_line_parts = lines[0].split(' ')
        if len(first_line_parts) != 3:
            return False
        method, path, version = first_line_parts

        if method not in ['GET']:
            return False

        # The version should be "HTTP/1.0"
        if version != "HTTP/1.0":
            return False

        # Check that all headers have the correct format
        for line in lines[1:]:
            if line == '':
                # An empty line indicates the end of the headers
                break
            if ':' not in line:
                # Headers should be of the form "Header-Name: header value"
                return False
            header_name, header_value = line.split(':', 1)
            if not header_name.strip() or not header_value.strip():
                # Header names and values should not be empty
                return False

        # The request is valid
        return True


def handle_client(client_socket):
    # Receive data from the client
    while True:
        try:
            request_bytes = client_socket.recv(4096) + b'\r\n'
            print(request_bytes.decode())
            print(request_bytes)
            request = HttpRequest(request_bytes.decode())
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            continue

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
    proxy_socket.bind(("localhost", 8081))
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
