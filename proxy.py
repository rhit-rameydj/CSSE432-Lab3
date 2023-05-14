import multiprocessing
import os
import socket
import sys
import threading
import traceback
import datetime
import time
import hashlib
import requests

import urllib.request
from urllib.parse import urlparse
from http.client import HTTPConnection
cached_urls = {}
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

def handle_client(client_socket):
    # Receive data from the client
    try:
        request_bytes = client_socket.recv(4096) + b'\r\n'
        request_bytes = request_bytes.decode().replace('HTTP/1.1', 'HTTP/1.0').replace('\r\nConnection: keep-alive', '').replace('\r\nUpgrade-Insecure-Requests: 1', '').encode()
        # print(request_bytes.decode())


        HttpRequest.verify_valid_http_request(request_bytes.decode())
        #I know full request is validated here
        request = HttpRequest(request_bytes.decode())
        handle_request(client_socket, request_bytes.decode(), request_bytes)



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




# Handle incoming requests
def handle_request(conn, request, request_bytes):
    method, path, version, headers = parse_request(request)
    httprequest = HttpRequest(request)
    if method == 'GET':
        cache_content = get_from_cache(path)
        if cache_content:
            print("Returning from cache...!!!CACHE HIT!!!")
            conn.sendall(cache_content)
        else:
            print("")
            content = forward_to_server(method, path, version, headers, httprequest, request_bytes)
            save_to_cache(path, content)
            conn.sendall(content)
    else:
        # Only handle GET requests
        conn.sendall(b'HTTP/1.0 405 Method Not Allowed\r\n\r\n')
    conn.close()

# Parse the incoming request
def parse_request(request):
    lines = request.strip().split('\r\n')
    method, path, version = lines[0].split()
    headers = {}
    for line in lines[1:]:
        name, value = line.split(': ', 1)
        headers[name.lower()] = value
    return method, path, version, headers

# Get content from cache if available
def get_from_cache(path):
    cache_filename = hashlib.md5(path.encode()).hexdigest()
    cache_filename = os.path.join("./cache/", cache_filename)

    try:
        with open(cache_filename, 'rb') as f:
            print("--------FILE FOUND_______")
            return f.read()
    except FileNotFoundError:

        return None
    # if path in cached_urls:
        # cache_filename = cached_urls[path]


# Forward the request to the server
def forward_to_server(method, path, version, headers, httprequest, request_bytes):
    # Connect to the server

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((httprequest.url, httprequest.port))

    # Forward the request
    request_line = f"{method} {path} {version}\r\n"
    header_lines = ''.join(f"{name}: {value}\r\n" for name, value in headers.items())
    request = request_line + header_lines + "\r\n"
    server_socket.sendall(request_bytes)

    # Get the response
    response = b''
    while True:
        data = server_socket.recv(1024)
        if not data:
            break
        response += data

    # Close the connection to the server
    server_socket.close()

    return response

# Save content to cache
def save_to_cache(path, content):
    cache_filename = hashlib.md5(path.encode()).hexdigest()
    cache_filename = os.path.join("./cache/", cache_filename)

    with open(cache_filename, 'wb') as f:
        print("------CACHING-----" + path)
        f.write(content)
    cached_urls[path] = cache_filename
# if __name__ == '__main__':
#     start_server()
def setup_conditional_get_request(url):
    # construct a datetime object representing the time two minutes ago
    print("CAlled at least once")
    two_minutes_ago = datetime.datetime.now() - datetime.timedelta(second=10)

    # convert the datetime object to a string in the format specified by the HTTP standard
    # e.g. "Tue, 15 Nov 1994 08:12:31 GMT"
    modified_since = two_minutes_ago.strftime('%a, %d %b %Y %H:%M:%S GMT')

    # create a request object with the URL and the If-Modified-Since header
    request = urllib.request.Request(url)
    request.add_header('If-Modified-Since', modified_since)

    return request

def check_for_webpage_updates():
    while True:
        print("HELLO FROM THE OUTSIDE")

        for url, filename in cached_urls.items():
            print(cached_urls.items())
            print("Right before")
            request = setup_conditional_get_request(url)
            try:

                with urllib.request.urlopen(request) as response:
                    if response.status == 200:
                        content = response.read()
                        with open(filename, 'wb') as f:
                            f.write(content)
                            print(f"Saved {url} to {filename}")
                    elif response.status == 304:
                        print(f"{url} not modified since last checked")
            except urllib.error.URLError as e:
                print(f"Error requesting {url}: {e.reason}")

        time.sleep(10)




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
        # update_thread = threading.Thread(target=check_for_webpage_updates, daemon=True)
        # update_thread.start()

        client_thread = threading.Thread(target=handle_client, args=(client_socket,), daemon=True)
        client_thread.start()



if __name__ == '__main__':
    main()
