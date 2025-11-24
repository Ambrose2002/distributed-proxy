import socket 
import cache_utils
import metrics
import threading
import json
import argparse

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
                            
        
    def fetch_from_origin(self, cache_key: str):
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
        
        response = {
            "status" : status,
            "data" : data,
            "cache_hit": cache_hit,
            "node": self.port
        }
        
        return json.dumps(response) + "\n"
        
    def build_cache_key(self, resource, key):
        return resource + "/" + key
    
def main(args):
    
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
    proxy_node = ProxyNode(args.host, args.port, args.origin_host, args.origin_port, args.ttl)
    proxy_node.start_server()

if __name__ == "__main__":
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
    
    args = parser.parse_args()
    
    main(args)
    