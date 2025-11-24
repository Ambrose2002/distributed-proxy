import socket
import threading
import argparse
import json
import time
from node_manager import NodeManager


class LoadBalancer:

    def __init__(self, host, port, proxy_list, strategy):
        """
        Initialize the load balancer.

        Parameters:
            host (str): Host for LB to listen on.
            port (int): Port for LB to listen on.
            proxy_list (list[(str,int)]): List of proxy nodes.
            strategy (str): 'round_robin' or 'least_loaded'.

        Internal State:
            - node_manager: Manages proxy health + failures.
            - proxy_stats: Stores metrics for each proxy.
            - current_index: Index for round-robin.
            - strategy: Load balancing policy.
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
        Starts the LB server.

        Behavior:
            - Create a TCP socket bound to (host,port).
            - Listen for connections.
            - For each connection:
                - Spawn thread for handle_client(conn, addr).
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
        Handles a single client connection.

        Behavior:
            - Read exactly one request line.
            - Choose a proxy using pick_proxy().
            - Forward the request to that proxy via forward_request().
            - Return the proxy response to the client.
            - On failure: return JSON error: PROXY_UNREACHABLE.
        """
        
        with conn:
            data = conn.recv(1024)
            
            if not data: return
            
            decoded_data = data.decode('utf-8')
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
        Determines which proxy should handle the next request.

        Behavior:
            - If strategy == 'round_robin':
                choose next healthy proxy in circular order.
            - If strategy == 'least_loaded':
                choose healthy proxy with lowest total_requests
                (from proxy_stats).
            - If no healthy proxies:
                fallback to all proxies.

        Returns: (host, port)
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
        Forwards the client request to the chosen proxy node.

        Parameters:
            proxy_host (str)
            proxy_port (int)
            raw_request (str): The actual request line ('GET article/1\n').

        Behavior:
            - Connect to proxy.
            - Send raw_request.
            - Read one newline-terminated JSON response.
            - Return the response string.
            - On failure:
                - mark proxy unhealthy in NodeManager
                - return PROXY_UNREACHABLE JSON
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
        Background thread that polls metrics from each proxy node.

        Behavior:
            - Runs forever.
            - Sleep for 2 seconds.
            - For each proxy:
                - Send 'METRICS\\n'.
                - Read reply.
                - If success: update proxy_stats and mark healthy.
                - If failure: mark unhealthy.
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
        Connect to a proxy and issue a METRICS request.

        Behavior:
            - Connect to proxy.
            - Send 'METRICS\\n'.
            - Read response line.
            - If status=='OK', return the metrics dict.
            - Else return None.
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
    Entry point for starting the Load Balancer.

    Steps:
        - Parse proxies from args.
        - Instantiate LoadBalancer.
        - Start metrics thread.
        - Call start_server().
    """
    pass


if __name__ == "__main__":
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