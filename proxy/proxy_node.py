import socket 
import cache_utils
import metrics
import threading

class ProxyNode:
    
    def __init__(self, host, port, origin_host, origin_port, ttl):
        self.host = host
        self.port = port
        self.origin_host = origin_host
        self.origin_port = origin_port
        self.ttl = ttl
        
        self.ttl_cache = cache_utils.TTLCache(ttl)
        self.proxy_metrics = metrics.ProxyMetrics()
        
    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(5)
            
            while True:
                
                conn, add = s.accept()
                    
                thread1 = threading.Thread(target=self.handle_connection, args = (conn, add))
                thread1.start()
                
        
    def handle_connection(self, conn, addr):
        
        with conn:
            data = conn.recv(1024)
            
            if not data:
                return
            
            try:
                data = data.decode('utf-8').strip()
                method, url = data.split(" ")
                
                if method != "GET":
                    res = self.build_response("WRONG_METHOD", "", False) 
                    conn.sendall(res.encode('utf-8'))
                    return
                
                resource, key = url.split("/", 1)
                
            except Exception as e:
                res = self.build_response("BAD_REQUEST", e, False)
                conn.sendall(res.encode('utf_8'))
                return
            
            cache_key = self.build_cache_key(resource, key)
                
            self.proxy_metrics.record_request()
            value, found = self.ttl_cache.get(cache_key)
            
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
                    self.ttl_cache.set(cache_key, value)
                    
                res = self.build_response(status, value, False)
                conn.sendall(res.encode('utf-8'))
                            
        
    def fetch_from_origin(self, key):
        ...
        
    def build_response(self, status : str, data, cache_hit : bool):
        ...
        
    def build_cache_key(resource, key):
        return resource + "/" + key