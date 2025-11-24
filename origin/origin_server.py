"""Origin Server for a Distributed Proxy System.

This server listens for incoming TCP connections and handles simple HTTP-like GET requests.
Clients send requests formatted as "METHOD /resource/key", where METHOD is currently only "GET".
The server responds with JSON-formatted messages indicating status and data payload.

The origin server serves as the authoritative source for requested resources, fetching data from
local JSON files stored under the 'data/' directory. It supports basic error handling for unsupported
methods and missing resources.

Request/Response Protocol:
- Requests: "METHOD /resource/key"
- Responses: JSON string with 'status' and 'data' fields, newline-terminated.

"""

import socket
import json
import time
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Create a TCP socket, bind to specified host and port, and listen for incoming connections
    s.bind((HOST, PORT))
    s.listen(5)

    # Main server loop: accept connections and process requests sequentially
    # Behavior:
    # - Accept a connection
    # - Read a single request line
    # - Parse method and URL
    # - Validate method (only GET supported)
    # - Fetch resource from local JSON file
    # - Send JSON-formatted response with status and data or error message
    # Constraints:
    # - Single request per connection
    # - Request format: "METHOD /resource/key"
    # - Response ends with newline character
    # Protocol expectations:
    # - Client sends UTF-8 encoded requests
    # - Server sends UTF-8 encoded JSON responses
    while True:

        conn, add = s.accept()

        with conn: 
            # Log connection with timestamp
            print(f"Connected by: {add} at {datetime.now()}")
            
            # Receive data from client
            data = conn.recv(1024)
            if not data:
                continue
            
            # Decode and parse request line
            data = data.decode('utf-8').strip()
            method, url = data.split(" ")
            
            # Validate HTTP method
            if method != "GET":
                # Prepare and send error response for unsupported methods
                res = {
                    "status": "WRONG_METHOD",
                    "data": f"{method} is not currently supported"
                }
                res_string = json.dumps(res) + "\n"
                time.sleep(0.1)
                conn.sendall(res_string.encode('utf-8'))
                
                continue
                
            # Parse resource and key from URL path
            resource, key = url.split("/", 1)
            filepath = "data/" + resource + key + ".json"
            print(f"{method} to file at {filepath}")
            
            # Attempt to load requested JSON file and send response
            try: 
                with open(filepath) as f:
                    fetched_data = json.load(f)
                res = {
                    "status": "OK",
                    "data": fetched_data
                }
                res_string = json.dumps(res) + "\n"
                time.sleep(0.1)
                conn.sendall(res_string.encode('utf-8'))
            except Exception as e:
                # Handle file not found or JSON errors
                res = {
                    "status": "NOT_FOUND",
                    "data": f"An error occured: {e}"
                }
                print(f"There was an error: {e}" )
                res_string = json.dumps(res) + "\n"
                time.sleep(0.1)
                conn.sendall(res_string.encode('utf-8'))