"""Load Balancer for Distributed Proxy System

This module implements a load balancer that distributes incoming client requests 
across multiple proxy nodes. It supports different load balancing strategies 
such as round-robin and least-loaded to optimize request handling and resource usage. 

The load balancer monitors the health and metrics of each proxy node, dynamically 
adjusting routing decisions based on node availability and performance. It acts as 
a centralized entry point for clients, forwarding requests to appropriate proxy nodes 
and aggregating metrics for monitoring purposes.
"""

import socket
import threading
import argparse
import json
import time
from node_manager import NodeManager


class LoadBalancer:
    """
    Represents a load balancer that manages a pool of proxy nodes and distributes client requests among them.

    Responsibilities:
    - Accept incoming client connections and requests.
    - Select an appropriate proxy node based on the configured load balancing strategy.
    - Forward client requests to the selected proxy node and relay responses back to the client.
    - Monitor the health and performance metrics of each proxy node.
    - Manage proxy node statuses (healthy/unhealthy) and update routing decisions accordingly.

    Interactions:
    - Uses NodeManager to track and update the health status of proxy nodes.
    - Communicates with proxy nodes over TCP sockets to forward requests and retrieve metrics.
    """

    def __init__(self, host, port, proxy_list, strategy):
        """
        Initialize the LoadBalancer instance.

        Parameters:
        - host (str): The IP address or hostname where the load balancer listens.
        - port (int): The port number where the load balancer listens.
        - proxy_list (list of tuples): List of proxy nodes as (host, port) tuples.
        - strategy (str): Load balancing strategy to use ("round_robin" or "least_loaded").

        Behavior:
        - Sets up internal structures for proxy management and metrics tracking.
        - Initializes a NodeManager instance for health monitoring of proxies.
        - Starts a background thread to periodically fetch metrics from proxies.

        Side Effects:
        - Starts a daemon thread for metrics collection.
        """
        self.host = host
        self.port = port
        self.proxy_list = proxy_list
        
        self.node_manager = NodeManager(proxy_list)
        self.proxy_stats = {}
        for proxy_host, proxy_port in proxy_list:
            self.proxy_stats[(proxy_host, proxy_port)] = None
            
        self.current_index = 0
        self.strategy = strategy
        
        self.metrics_thread = threading.Thread(target=self.metrics_loop, daemon=True)
        self.metrics_thread.start()


    def start_server(self):
        """
        Start the load balancer server to accept incoming client connections.

        Behavior:
        - Creates a TCP socket bound to the configured host and port.
        - Listens for incoming client connections.
        - For each accepted connection, spawns a new thread to handle the client request.

        Side Effects:
        - Runs indefinitely, accepting and handling client connections concurrently.

        Error Handling:
        - Exceptions during socket operations are not explicitly caught here and will propagate.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(5)
            
            while True:
                
                conn, add = s.accept()
                
                thread1 = threading.Thread(target=self.handle_client, args = (conn, add))
                thread1.start()


    def handle_client(self, conn, addr):
        """
        Handle an individual client connection.

        Parameters:
        - conn (socket.socket): The socket connection to the client.
        - addr (tuple): The client address.

        Behavior:
        - Receives data from the client.
        - If the client requests "METRICS", returns the current load balancer and proxy metrics.
        - Otherwise, selects a proxy node based on the strategy and forwards the client's request.
        - Sends the response from the proxy back to the client.
        - Handles proxy unreachability by sending appropriate error responses.

        Side Effects:
        - May mark proxy nodes as healthy or unhealthy based on communication success.
        - Sends data back to the client over the socket.

        Error Handling:
        - If no data is received, returns immediately.
        - If forwarding fails, sends error JSON responses to client.
        """
        with conn:
            data = conn.recv(1024)
            
            if not data: return
            
            decoded_data = data.decode('utf-8')
            
            if decoded_data.strip() == "METRICS":
                
                res = {}
                res["status"] = "OK"
                data = {}
                data["strategy"] = self.strategy
                data["current_index"] = self.current_index
                data["proxies"] = {}
                
                for proxy_host, proxy_port in self.proxy_list:
                    proxy_str = f"{proxy_host}:{proxy_port}"
                    proxy_stat = {}
                    proxy_stat["healthy"] = self.node_manager.is_healthy(proxy_host, proxy_port)
                    proxy_stat["metrics"] = self.proxy_stats[(proxy_host, proxy_port)]
                    data["proxies"][proxy_str] = proxy_stat 
                res["data"] = data
                
                conn.sendall((json.dumps(res) + "\n").encode('utf-8'))
                return 
            
            decoded_data = decoded_data.strip() + "\n"
            
            proxy = self.pick_proxy()
            
            if proxy is not None:
                proxy_host, proxy_port = proxy
            
                res = self.forward_request(proxy_host, proxy_port, decoded_data)
                
                if res:
                    conn.sendall(res.encode('utf-8'))
                    return
                else:
                    response = {
                        "status": "PROXY_UNREACHABLE", 
                        "data": None
                    }
                    conn.sendall((json.dumps(response) + "\n").encode('utf-8'))
            else:
                response = {
                    "status": "PROXY_ERROR", 
                    "data": None
                }
                conn.sendall((json.dumps(response) + "\n").encode('utf-8'))


    def pick_proxy(self):
        """
        Select a proxy node based on the configured load balancing strategy.

        Returns:
        - tuple: (host, port) of the selected proxy node.
        - None: if no proxies are available.

        Behavior:
        - Filters to healthy proxies if any exist; otherwise uses all proxies.
        - If strategy is "round_robin", selects proxies in cyclic order.
        - If strategy is "least_loaded", selects the proxy with the fewest total requests.

        Side Effects:
        - Updates the current index counter for round robin strategy.

        Error Handling:
        - Assumes proxy_stats entries may be None and treats them as zero load.
        """
        healthy_proxies = self.node_manager.get_healthy_nodes()
        if not healthy_proxies:
            healthy_proxies = self.proxy_list
        if self.strategy == "round_robin":
            idx = self.current_index % len(healthy_proxies)
            proxy = healthy_proxies[idx]
            self.current_index += 1
            return proxy
        
        elif self.strategy == "least_loaded":
            return min(healthy_proxies, 
                       key = lambda client :  self.proxy_stats[client]["total_requests"] if self.proxy_stats[client] else 0)


    def forward_request(self, proxy_host, proxy_port, raw_request):
        """
        Forward a client request to a specified proxy node and retrieve the response.

        Parameters:
        - proxy_host (str): Hostname or IP of the proxy node.
        - proxy_port (int): Port number of the proxy node.
        - raw_request (str): The raw request string to forward.

        Returns:
        - str: JSON-formatted response string from the proxy node, including newline.
        - None: If the proxy is unreachable or response invalid.

        Behavior:
        - Establishes a TCP connection to the proxy node.
        - Sends the raw request.
        - Reads a single line response and attempts to parse it as JSON.
        - Marks the proxy node as healthy if response is valid.
        - Marks the proxy node as unhealthy if connection or response fails.

        Side Effects:
        - Updates node health status via NodeManager.
        - Opens and closes socket connections.

        Error Handling:
        - Catches connection errors and JSON parsing errors.
        - Returns error JSON strings on failure.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        f = None
        
        try:
            try:
                s.connect((proxy_host, proxy_port))
            except Exception as e:
                self.node_manager.mark_unhealthy(proxy_host, proxy_port)
                response = {
                        "status": "PROXY_UNREACHABLE", 
                        "data": str(e)
                }
                return json.dumps(response) + "\n"

            f = s.makefile('r', encoding = 'utf-8', newline = "\n")
            s.sendall(raw_request.encode('utf-8'))
            
            first_line = f.readline()
            if first_line:
                j_string = first_line.strip()
                
                try:
                    json.loads(j_string)
                except Exception as e:
                    self.node_manager.mark_unhealthy(proxy_host, proxy_port)
                    response = {"status": "PROXY_UNREACHABLE", "data": str(e)}
                    return json.dumps(response) + "\n"
                self.node_manager.mark_healthy(proxy_host, proxy_port)
                return j_string + "\n"
        finally:
            if f:
                f.close()
            s.close()
            
        self.node_manager.mark_unhealthy(proxy_host, proxy_port)
        response = {
                        "status": "PROXY_UNREACHABLE", 
                        "data": None
        } 
        return json.dumps(response) + "\n"

    def metrics_loop(self):
        """
        Background loop that periodically requests and updates metrics from all proxy nodes.

        Behavior:
        - Runs indefinitely, waking every 2 seconds.
        - Requests metrics from each proxy node by connecting and sending a "METRICS" request.
        - Updates internal proxy_stats dictionary with the latest metrics.
        - Marks proxies as healthy or unhealthy based on metrics retrieval success.
        - Logs exceptions and continues running.

        Side Effects:
        - Updates proxy health status and metrics.
        - Runs as a daemon thread.

        Error Handling:
        - Catches and logs all exceptions to prevent thread termination.
        """
        while True:
            try:
                time.sleep(2)
                for proxy_host, proxy_port in self.proxy_list:
                    metrics = self.request_metrics(proxy_host, proxy_port)
                    if metrics:
                        self.proxy_stats[(proxy_host, proxy_port)] = metrics
                        self.node_manager.mark_healthy(proxy_host, proxy_port)
                    else:
                        self.proxy_stats[(proxy_host, proxy_port)] = None
                        self.node_manager.mark_unhealthy(proxy_host, proxy_port)
            except Exception as e:
                print(f"[MetricsLoopError] {e}")
                continue


    def request_metrics(self, host, port):
        """
        Request metrics data from a single proxy node.

        Parameters:
        - host (str): Hostname or IP of the proxy node.
        - port (int): Port number of the proxy node.

        Returns:
        - dict: Parsed metrics data if successful.
        - None: If unable to connect or parse metrics.

        Behavior:
        - Connects to the proxy node over TCP.
        - Sends a "METRICS\n" request.
        - Reads a single line response and attempts to parse it as JSON.
        - Validates the response status and extracts data.

        Side Effects:
        - Opens and closes socket connections.

        Error Handling:
        - Returns None on connection failures or invalid JSON responses.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        f = None
        
        try:
            try:
                s.connect((host, port))
            except Exception:
                return None
            
            f = s.makefile('r', encoding = 'utf-8', newline = '\n')
            request = "METRICS\n"
            s.sendall(request.encode('utf-8'))
            
            first_line = f.readline()
            if first_line:
                j_string = first_line.strip()
                
                try:
                    res = json.loads(j_string)
                except Exception:
                    return None
                
                if res["status"] == "OK" and "data" in res:
                    return res["data"]
                return None
            else:
                return None
        finally:
            if f:
                f.close()
            s.close()
        

def main(args):
    """
    Main entry point for the load balancer CLI.

    Parameters:
    - args (argparse.Namespace): Parsed command-line arguments.

    Expected CLI Arguments:
    - --host (str): Host/IP to bind the load balancer (default: 127.0.0.1).
    - --port (int): Port number to bind the load balancer (required).
    - --proxies (list of str): List of proxy nodes in "host:port" format.
    - --strategy (str): Load balancing strategy, either "round_robin" or "least_loaded" (default: "round_robin").

    Behavior:
    - Parses and validates proxy node addresses.
    - Validates the load balancing strategy.
    - Instantiates and starts the LoadBalancer server.

    Side Effects:
    - Prints error messages for invalid arguments or configurations.
    - Runs the load balancer server indefinitely upon successful start.
    """
    try:
        proxies = args.proxies
        
        if not proxies:
            print(f"No proxies given")
            return
        
        proxy_list = []
        
        for proxy in proxies:
            host, port = proxy.split(":")
            proxy_list.append((host, int(port)))
    except Exception as e:
        print(f"Error parsing args: {str(e)}")
        return
    
    if args.strategy not in ["round_robin", "least_loaded"]:
        print(f"{args.strategy} is not a supported strategy")
        return
    
    print(f"Load Balancer starting on {args.host}:{args.port}")
    load_balancer = LoadBalancer(args.host, args.port, proxy_list, args.strategy)
    load_balancer.start_server()


if __name__ == "__main__":
    """
    Command-line interface for starting the load balancer.

    Usage example:
    python load_balancer.py --host 127.0.0.1 --port 8000 --proxies 127.0.0.1:9000 127.0.0.1:9001 --strategy round_robin

    This block parses CLI arguments and invokes the main function to start the server.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)

    parser.add_argument(
        "--proxies",
        type=str,
        nargs="+",
        help="List of proxies as host:port host:port ..."
    )

    parser.add_argument(
        "--strategy",
        type=str,
        choices=["round_robin", "least_loaded"],
        default="round_robin"
    )

    args = parser.parse_args()
    main(args)