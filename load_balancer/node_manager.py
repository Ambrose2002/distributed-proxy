"""
NodeManager is responsible for managing the health status of proxy nodes in the load balancer subsystem.
It tracks the health of each proxy node, marking nodes as healthy or unhealthy based on failure counts,
and provides thread-safe access to the current set of healthy nodes for load balancing decisions.
"""

import threading

class NodeManager:
    """
    Manages the health states of proxy nodes used by the load balancer.

    Responsibilities:
    - Track health and failure counts of proxy nodes.
    - Provide thread-safe updates and queries of node health.
    - Determine which nodes are currently healthy for routing traffic.

    Thread Safety:
    All methods that modify or access shared node state use a threading.Lock to ensure safe concurrent access.

    Failure Model:
    Nodes are marked unhealthy after exceeding a maximum number of consecutive failures (default 3).
    Nodes can be marked healthy again to reset failure counts.
    """
    
    def __init__(self, proxy_list):
        """
        Initialize the NodeManager with a list of proxy nodes.

        Parameters:
        - proxy_list: List of tuples (host, port) representing proxy nodes.

        Behavior:
        Initializes internal state tracking health and failure counts for each node.
        Assumes all nodes start as healthy with zero failures.

        Concurrency:
        Initializes internal lock for thread-safe operations.
        """
        self.proxy_list = proxy_list
        self.nodes = {}
        
        for host, port in self.proxy_list:
            self.nodes[(host, port)] = {
                "healthy": True, 
                "failures": 0
            }
        self.lock = threading.Lock()
        self.max_failures = 3
        
    def mark_healthy(self, host, port):
        """
        Mark the specified node as healthy and reset its failure count.

        Parameters:
        - host: The hostname or IP address of the node.
        - port: The port number of the node.

        Behavior:
        Sets the node's 'healthy' status to True and resets failure count to zero.

        Concurrency:
        Acquires internal lock to safely update shared state.
        """
        with self.lock:
            self.nodes[(host, port)]["healthy"] = True
            self.nodes[(host, port)]["failures"] = 0
            
    def mark_unhealthy(self, host, port):
        """
        Increment the failure count for the specified node and mark unhealthy if threshold exceeded.

        Parameters:
        - host: The hostname or IP address of the node.
        - port: The port number of the node.

        Behavior:
        Increments the failure count for the node. If failure count reaches or exceeds max_failures,
        marks the node as unhealthy.

        Concurrency:
        Acquires internal lock to safely update shared state.
        """
        with self.lock:
            self.nodes[(host, port)]["failures"] += 1
            
            if self.nodes[(host, port)]["failures"] >= self.max_failures:
                self.nodes[(host, port)]["healthy"] = False
                
    
    def get_healthy_nodes(self):
        """
        Retrieve the list of currently healthy nodes.

        Returns:
        - List of (host, port) tuples representing nodes marked as healthy.
          If no nodes are healthy, returns the full list of proxy nodes.

        Concurrency:
        Acquires internal lock to safely read shared state.
        """
        with self.lock:
            healthy_nodes = list(filter(lambda x : self.nodes[x]["healthy"], self.proxy_list))
            
            return healthy_nodes if healthy_nodes else self.proxy_list
        
    def get_all_nodes(self):
        """
        Retrieve the full list of proxy nodes managed by this NodeManager.

        Returns:
        - List of (host, port) tuples representing all nodes.

        Concurrency:
        This method returns a reference to the original proxy_list and does not acquire a lock.
        The proxy_list is assumed to be immutable after initialization.
        """
        return self.proxy_list
    
    def is_healthy(self, host, port):
        """
        Check if the specified node is currently marked as healthy.

        Parameters:
        - host: The hostname or IP address of the node.
        - port: The port number of the node.

        Returns:
        - True if the node is healthy, False otherwise.

        Concurrency:
        Acquires internal lock to safely read shared state.
        """
        with self.lock:
            return self.nodes[(host, port)]["healthy"]