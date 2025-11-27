"""ProxyNode is a TCP server that acts as a proxy cache node in a distributed caching system.
It listens for client requests, serves cached data when available, fetches data from an origin server on cache misses,
and reports metrics on request handling. The proxy node expects requests in the format "GET resource/key" or the special
command "METRICS" to retrieve performance statistics. Responses are JSON-encoded with status, data, cache hit info, and node port.
"""

import socket 
import cache_utils
import metrics
import threading
import json
import argparse

class ProxyNode:
    """
    ProxyNode manages incoming TCP connections to serve cached data or fetch from an origin server.
    It integrates a TTL-based cache, records metrics on hits, misses, and origin fetches, and supports concurrent client handling
    via threading. It implements a simple text-based protocol where clients send GET requests or METRICS commands,
    and receive JSON-formatted responses indicating status and data.
    Supports two cache types: "ttl" and "lru", using TTLCache or LRUCache accordingly.
    """
    
    def __init__(self, host, port, origin_host, origin_port, cache_type, ttl, lru_capacity):
        """
        Initialize the ProxyNode with network parameters and caching TTL.

        Parameters:
            host (str): Host address to bind the proxy server.
            port (int): Port number to bind the proxy server.
            origin_host (str): Host address of the origin server.
            origin_port (int): Port number of the origin server.
            cache_type (str): "ttl" or "lru", selects which cache implementation to use.
            ttl (int): TTL in seconds for TTLCache.
            lru_capacity (int): Maximum number of entries for LRUCache.

        Side Effects:
            Creates an internal TTLCache or LRUCache instance based on cache_type and a ProxyMetrics instance.

        Raises:
            None.
        """
        self.host = host
        self.port = port
        self.origin_host = origin_host
        self.origin_port = origin_port
        
        if cache_type == "ttl":
            self.cache = cache_utils.TTLCache(ttl)
        else:
            self.cache = cache_utils.LRUCache(lru_capacity)
        self.proxy_metrics = metrics.ProxyMetrics()
        
    def start_server(self):
        """
        Start the TCP server to listen for incoming client connections.

        Behavior:
            Binds to the configured host and port, listens for connections,
            and spawns a new thread to handle each connection concurrently.
            Each connection is handled concurrently and this method blocks indefinitely.

        Side Effects:
            Opens a socket and runs an infinite loop accepting connections.

        Raises:
            Any socket errors during bind or listen will propagate.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(5)
            
            while True:
                
                conn, add = s.accept()
                    
                thread1 = threading.Thread(target=self.handle_connection, args = (conn, add))
                thread1.start()
                
        
    def handle_connection(self, conn, addr):
        """
        Handle a single client connection.

        Parameters:
            conn (socket.socket): The client connection socket.
            addr (tuple): The client address.

        Behavior:
            Reads a request from the client, processes GET or METRICS commands,
            serves cached data or fetches from origin, and sends JSON-formatted responses.
            If cache_type is LRU, recency is updated on each get/set.

        Side Effects:
            Updates metrics for requests, hits, misses, and origin fetches.
            May update the internal cache on origin fetch success.

        Error Handling:
            Returns error responses on malformed requests or unsupported methods.
            Closes the connection after handling.

        Returns:
            None.
        """
        
        with conn:
            data = conn.recv(1024)
            
            if not data:
                return
            
            try:
                data = data.decode('utf-8').strip()
                
                if data == "METRICS":
                    metrics_dict = self.proxy_metrics.report()
                    res = {}
                    res["status"] = "OK"
                    res["data"] = metrics_dict
                    
                    res_string = json.dumps(res) + "\n"
                    conn.sendall(res_string.encode('utf-8'))
                    return
                
                method, url = data.split(" ")
                
                if method != "GET":
                    res = self.build_response(f"WRONG_METHOD: {method}", "", False) 
                    conn.sendall(res.encode('utf-8'))
                    return
                
                resource, key = url.split("/", 1)
                
            except Exception as e:
                res = self.build_response("BAD_REQUEST", str(e), False)
                conn.sendall(res.encode('utf-8'))
                return
            
            cache_key = self.build_cache_key(resource, key)
                
            self.proxy_metrics.record_request()
            value, found = self.cache.get(cache_key)
            
            if found:
                self.proxy_metrics.record_hit()
                res = self.build_response("OK", value, True)
                conn.sendall(res.encode('utf-8'))
                return
                
            else:
                self.proxy_metrics.record_miss()
                self.proxy_metrics.record_origin_fetch()
                value, status = self.fetch_from_origin(cache_key)
                
                if status == "OK":
                    self.cache.set(cache_key, value)
                    
                res = self.build_response(status, value, False)
                conn.sendall(res.encode('utf-8'))
                            
        
    def fetch_from_origin(self, cache_key: str):
        """
        Fetch the data corresponding to cache_key from the origin server.

        Parameters:
            cache_key (str): The resource/key string to request from the origin.

        Behavior:
            Opens a TCP connection to the origin server, sends a GET request,
            reads a JSON response, and parses status and data.

        Returns:
            tuple: (data, status)
                data: The retrieved data if status is "OK", else None.
                status: One of "OK", "NOT_FOUND", or "ORIGIN_FAILURE".
                The status may be "ORIGIN_FAILURE" when connection or parse fails.

        Side Effects:
            Opens and closes a socket connection to the origin server.

        Error Handling:
            Returns ("None", "ORIGIN_FAILURE") on connection errors,
            malformed responses, or unexpected status.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        f = None
        try:
            try:
                s.connect((self.origin_host, self.origin_port))
            except Exception as e:
                return (None, "ORIGIN_FAILURE")
            
            f = s.makefile('r', encoding='utf-8', newline='\n')
            request = f"GET {cache_key}\n"
            s.sendall(request.encode('utf-8'))
            
            first_line = f.readline()
            if first_line:
                j_string = first_line.strip()
                
                try:
                    res = json.loads(j_string)
                except Exception as e:
                    return (None, "ORIGIN_FAILURE")
                
                if res["status"] == "OK":
                    return (res["data"], "OK")
                elif res["status"] == "NOT_FOUND":
                    return (None, "NOT_FOUND")
                else:
                    return (None, "ORIGIN_FAILURE")
        finally:
            if f:
                f.close()
            s.close()                 
        return (None, "ORIGIN_FAILURE")    
            
        
    def build_response(self, status : str, data, cache_hit : bool):
        """
        Build a JSON-formatted response string for client.

        Parameters:
            status (str): Status string indicating request outcome.
            data: The payload data to include in the response.
            cache_hit (bool): Whether the response data was served from cache.

        Returns:
            str: JSON string with fields "status", "data", "cache_hit", and "node",
                 terminated by a newline character. The node field indicates which proxy node served the request.

        Side Effects:
            None.
        """
        
        response = {
            "status" : status,
            "data" : data,
            "cache_hit": cache_hit,
            "node": self.port
        }
        
        return json.dumps(response) + "\n"
        
    def build_cache_key(self, resource, key):
        """
        Construct a cache key string from resource and key.

        Parameters:
            resource (str): The resource name.
            key (str): The key within the resource.

        Returns:
            str: Concatenated cache key in the form "resource/key".

        Side Effects:
            None.
        """
        return resource + "/" + key
    
def main(args):
    """
    Main entry point for running the ProxyNode from the command line.

    Parameters:
        args (argparse.Namespace): Parsed command line arguments with attributes:
            - host (str): Host to bind the proxy.
            - port (int): Port to bind the proxy. Must be > 1024.
            - origin_host (str): Origin server host.
            - origin_port (int): Origin server port. Must be > 1024.
            - ttl (int): Cache time-to-live in seconds.
            - cache_type (str): Cache implementation type, either "ttl" or "lru".
            - lru_capacity (int): Maximum number of entries for LRUCache.

    Behavior:
        Validates port arguments, prints error messages if invalid,
        initializes and starts the ProxyNode server.

    Side Effects:
        Prints status messages to stdout.
        Runs a blocking server loop.

    Returns:
        None.

    Example usage:
        python proxy_node.py --port 9000 --host 127.0.0.1 --origin_host 127.0.0.1 --origin_port 8000 --ttl 30 --cache_type ttl --lru_capacity 3
    """
    
    if args.port < 1024:
        print("port must be greater than 1024")
        return
    if args.origin_port < 1024:
        print("origin_port must be greater than 1024")
        return
        
    if args.port == args.origin_port:
        print("port and origin_port cannot be the same")
        return
    
    print(f"Proxy node starting on {args.host}:{args.port}")
    proxy_node = ProxyNode(args.host, args.port, args.origin_host, args.origin_port, args.cache_type, args.ttl, args.lru_capacity)
    proxy_node.start_server()

if __name__ == "__main__":
    """
    Command-line interface to run the ProxyNode.

    Usage:
        python proxy_node.py --port <port> [--host <host>] [--origin_host <origin_host>]
                             [--origin_port <origin_port>] [--ttl <ttl>] [--cache_type <ttl|lru>] [--lru_capacity <int>]

    Required Arguments:
        --port: Port number for the proxy server (must be > 1024).

    Optional Arguments:
        --host: Host address for the proxy server (default 127.0.0.1).
        --origin_host: Host address of the origin server (default 127.0.0.1).
        --origin_port: Port of the origin server (default 8000, must be > 1024).
        --ttl: Cache time-to-live in seconds (default 30).
        --cache_type: Cache implementation type, either "ttl" or "lru".
        --lru_capacity: Maximum number of entries for LRUCache (default 3).
    """
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "--host",
        type = str,
        default = "127.0.0.1"
    )
    
    parser.add_argument(
        "--port",
        type = int,
        required=True
    )
    
    parser.add_argument(
        "--origin_host",
        type = str,
        default = "127.0.0.1"
    )
    
    parser.add_argument(
        "--origin_port",
        type = int,
        default = 8000
    )
    
    parser.add_argument(
        "--ttl",
        type = int,
        default = 30
    )
    
    parser.add_argument(
        "--cache_type",
        type = str,
    )
    
    parser.add_argument(
        "--lru_capacity",
        type = int,
        default = 3
    )
    
    args = parser.parse_args()
    
    main(args)