"""Metrics subsystem for the proxy server.

This module defines the ProxyMetrics class, which tracks various metrics related to proxy operations,
including total requests, cache hits and misses, and origin fetches. These metrics help monitor
the performance and behavior of the proxy server.
"""

from datetime import datetime

class ProxyMetrics:
    """
    Tracks proxy server metrics such as total requests, cache hits, cache misses, and origin fetches.

    These metrics provide insight into the proxy's effectiveness and performance. The class assumes
    single-threaded usage or external synchronization if used in a multi-threaded environment, as it
    does not implement internal thread-safety mechanisms.
    """
    
    def __init__(self):
        """
        Initializes a new ProxyMetrics instance with all counters set to zero and records the start time.

        No parameters.

        Side effects:
            - Sets counters for total requests, cache hits, cache misses, and origin fetches to zero.
            - Records the start time of metric tracking.
        """
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.origin_fetches = 0
        self.start_time = datetime.now()
        
    def record_request(self):
        """
        Increments the total number of requests processed by the proxy.

        No parameters.

        Side effects:
            - Increments the total_requests counter by one.
        """
        self.total_requests += 1
        
    def record_hit(self):
        """
        Increments the count of cache hits.

        No parameters.

        Side effects:
            - Increments the cache_hits counter by one.
        """
        self.cache_hits += 1
        
    def record_miss(self):
        """
        Increments the count of cache misses.

        No parameters.

        Side effects:
            - Increments the cache_misses counter by one.
        """
        self.cache_misses += 1
        
    def record_origin_fetch(self):
        """
        Increments the count of origin fetches performed by the proxy.

        No parameters.

        Side effects:
            - Increments the origin_fetches counter by one.
        """
        self.origin_fetches += 1
        
    def report(self):
        """
        Generates a report dictionary containing current metrics and statistics.

        No parameters.

        Returns:
            dict: A dictionary with the following keys:
                - 'start_time': ISO formatted start time string.
                - 'total_requests': Total number of requests processed.
                - 'hit_rate': Ratio of cache hits to total cache accesses (hits + misses).
                - 'hits': Number of cache hits.
                - 'misses': Number of cache misses.
                - 'origin_fetches': Number of origin fetches performed.
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            hit_rate = 0
        else:
            hit_rate = self.cache_hits / total
        return {
            "start_time": self.start_time.isoformat(),
            "total_requests": self.total_requests,
            "hit_rate": hit_rate,
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "origin_fetches": self.origin_fetches
        }
        
    def get_total_requests(self):
        """
        Returns the total number of requests processed by the proxy.

        No parameters.

        Returns:
            int: The total number of requests recorded.
        """
        return self.total_requests