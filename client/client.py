"""Client for sending requests to a distributed proxy server.

This client connects to a specified host and port, sends HTTP-like GET requests or special METRICS requests,
and prints the JSON response received from the server.

Usage:
    python client.py --port <port> [--host <host>] [--get <endpoint>] [--metrics]

Behavior:
- If --metrics flag is provided, sends a METRICS request to the server.
- If --get <endpoint> is provided, sends a GET request for the specified endpoint.
- If neither --metrics nor --get is provided, prints an error message.
- Handles connection errors gracefully by returning a JSON error response.
"""

import socket
import json
import argparse
import time

def build_request(path):
    """
    Constructs a simple HTTP-like GET request string for the given path.

    Parameters:
        path (str): The endpoint path to request from the server.

    Returns:
        str: A GET request string formatted as "GET <path>\n".
    
    Behavior:
        The returned string is intended to be sent over a socket to the server.
    """
    return f"GET {path}\n"


def send_request(host, port, request_str):
    """
    Sends a request string to the specified host and port using a TCP socket and returns the JSON response.

    Parameters:
        host (str): The IP address or hostname of the server to connect to.
        port (int): The port number on which the server is listening.
        request_str (str): The request string to send, expected to be newline-terminated.

    Returns:
        dict or str: The parsed JSON response from the server as a dictionary if successful,
                     or a JSON-formatted error string if a connection error occurs or no response is received.

    Socket Behavior:
        - Opens a TCP socket connection to the server.
        - Sends the encoded request string.
        - Reads a single line from the server, expecting a newline-terminated JSON string.
        - Closes the socket and associated file object after communication.

    Error Handling:
        - If the connection fails or no response is received, returns a JSON string indicating CLIENT_CONNECTION_ERROR.

    Protocol Assumptions:
        - The server responds with a single line of JSON terminated by a newline character.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    f = None

    try:
        try:
            s.connect((host, port))
        except Exception as e:
            response = {
                "status": "CLIENT_CONNECTION_ERROR",
                "data": None
            }
            res = json.dumps(response) + '\n'
            return res

        f = s.makefile('r', encoding='utf-8', newline='\n')
        s.sendall(request_str.encode('utf-8'))

        first_line = f.readline()

        if first_line:
            return first_line
        else:
            response = {
                "status": "CLIENT_CONNECTION_ERROR",
                "data": None
            }
            res = json.dumps(response) + '\n'
            return res
    finally:
        if f:
            f.close()
        s.close()


def run(args):
    """
    Runs the client logic based on parsed command-line arguments.

    Parameters:
        args (argparse.Namespace): Parsed command-line arguments.

    Behavior:
        - If --metrics flag is set, sends a "METRICS\n" request and prints the JSON response.
        - If --get <endpoint> is provided, sends a GET request for the specified endpoint and prints the JSON response.
        - If neither --metrics nor --get is provided, prints an error message indicating that GET endpoint must be provided.
    """
    if args.metrics:
        request_str = "METRICS\n"
        start_time = time.time()
        res = json.loads(send_request(args.host, args.port, request_str))
        end_time = time.time()
        res["latency_ms"] = (end_time - start_time) * 1000
        print(json.dumps(res, indent=4))
        return

    if not args.get:
        print("Error: GET endpoint must be provided")
        return
    url = args.get
    request_str = build_request(url)
    start_time = time.time()
    res = json.loads(send_request(args.host, args.port, request_str))
    end_time = time.time()
    res["latency_ms"] = (end_time - start_time) * 1000
    print(json.dumps(res, indent=4))


if __name__ == "__main__":
    """
    Command-line interface for the client.

    Arguments:
        --host (str): Hostname or IP address of the server (default: 127.0.0.1).
        --port (int): Port number of the server (required).
        --get (str): Endpoint path for GET request.
        --metrics (flag): If set, sends a METRICS request instead of GET.

    Example usage:
        python client.py --port 8080 --get /status
        python client.py --host 192.168.1.10 --port 8080 --metrics
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1"
    )

    parser.add_argument(
        "--metrics",
        action="store_true"
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True
    )

    parser.add_argument(
        "--get",
        type=str,
    )

    args = parser.parse_args()
    run(args)