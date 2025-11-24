import threading

class NodeManager:
    
    def __init__(self, proxy_list):
        
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
        
        with self.lock:
            self.nodes[(host, port)]["healthy"] = True
            self.nodes[(host, port)]["failures"] = 0
            
    def mark_unhealthy(self, host, port):
        
        with self.lock:
            self.nodes[(host, port)]["failures"] += 1
            
            if self.nodes[(host, port)]["failures"] >= self.max_failures:
                self.nodes[(host, port)]["healthy"] = False
                
    
    def get_healthy_nodes(self):
        with self.lock:
            healthy_nodes = list(filter(lambda x : self.nodes[x]["healthy"], self.proxy_list))
            
            return healthy_nodes if healthy_nodes else self.proxy_list
        
    def get_all_nodes(self):
        return self.proxy_list
    
    def is_healthy(self, host, port):
        with self.lock:
            return self.nodes[(host, port)]["healthy"]
        
    