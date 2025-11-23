from datetime import datetime

class ProxyMetrics:
    
    def __init__(self):
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.origin_fetches = 0
        self.start_time = datetime.now()
        
    def record_request(self):
        self.total_requests += 1
        
    def record_hit(self):
        self.cache_hits += 1
        
    def record_miss(self):
        self.cache_misses += 1
        
    def record_origin_fetch(self):
        self.origin_fetches += 1
        
    def report(self):
        total = self.cache_hits + self.cache_misses
        if total == 0:
            hit_rate = 0
        else:
            hit_rate = self.cache_hits / total
        return {
            "start_time": self.start_time,
            "total_requests": self.total_requests,
            "hit_rate": hit_rate,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "origin_fetches": self.origin_fetches
        }