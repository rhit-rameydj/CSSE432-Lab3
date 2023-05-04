import os
import socket
import sys
import threading
import traceback
import datetime
import time
import hashlib
import requests

from urllib.parse import urlparse
from http.client import HTTPConnection


class BadRequestException(Exception):
    pass


class NotImplementedException(Exception):
    pass


class HttpRequest:
    def __init__(self, request):
        split = request.split()
        self.method = split[0]
        self.fullurl = split[1]
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
        print(path)
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

class Cache:
    def __init__(self):
        self.store_path = './cache/'

    def check_cache(self, req_to_check):
        print("Check cache for request here???")

    def cache_request(self, req_to_cache):
        print("Write response from server to file for cache")

    def do_conditional_get(self):
        print("!!!Making conditional get for cached web-pages!!!")
        last_modified = None

        while True:
            # Send an HTTP request with the If-Modified-Since header
            headers = {}
            if last_modified:
                headers['If-Modified-Since'] = last_modified
            response = ""
            #requests.get(url, headers=headers)

            # Check if the response is a 304 Not Modified status code
            if response.status_code == 304:
                print('Resource not modified since', last_modified)
                time.sleep(180)  # Wait for 180 seconds before checking again
                continue

            # Parse the Last-Modified header from the response
            last_modified = response.headers.get('Last-Modified')

            # Cache the response data here
            # ...

            print('Resource modified on', last_modified)

            time.sleep(180)  # Wait for 180 seconds before checking again




def do_process(client_socket, request, request_bytes):
    cache = Cache()
    fullurl = request.fullurl
    filename = generate_filename(fullurl)

    if filename:
        print(filename)

    filetouse = cache.store_path + filename
    print(filetouse)
    if os.path.exists(filetouse):
        f = open(filetouse[1:], "r")
        outputdata = f.readlines()
        # ProxyServer finds a cache hit and generates a response message
        client_socket.send("HTTP/1.0 200 OK\r\n")
        client_socket.send("Content-Type:text/html\r\n")
        for data in outputdata:
            client_socket.send(data)
        print("!!!!READ FROM CACHE!!!!")
    else:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Before sending check cache here for content requested
        # modify request_bytes to be conditional get
        # If-Modified-Since two minutes ago
        server_socket.connect((request.url, request.port))
        server_socket.send(request_bytes)
        response = b''
        while True:
            data = server_socket.recv(4096)
            if not data:
                break
            response += data
            # Create a new file in the cache for the requested file.

            # Also send the response in the buffer to client socket and the
            # corresponding file in the cache
        # do not write the response to the file
        print(response)
        server_socket.close()
        tmpFile = open(filetouse, "wb")
        for data in response:
            tmpFile.write(data)
        client_socket.sendall(response)


    client_socket.close()  # Close the client and the server sockets



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

    do_process(client_socket, request, request_bytes)

def generate_filename(url):
    # Encode the URL as UTF-8 and hash it using SHA-256
    url_bytes = url.encode('utf-8')
    hash_bytes = hashlib.sha256(url_bytes).digest()
    # Convert the hash bytes to a hexadecimal string
    hash_hex = hash_bytes.hex()
    # Add a file extension to the hexadecimal string and return it as the filename
    return hash_hex + '.html'

def write_file(url, filename):
    # Send an HTTP request to fetch the webpage
    HTTPConnection._http_vsn_str = 'HTTP/1.0'
    response = requests.get(url)
    # Open a file for writing the webpage bytes
    if response.status_code == "200":
        with open(filename, 'wb') as f:
            # Write the webpage bytes to the file
            f.write(response.content)


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
