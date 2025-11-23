import threading
from datetime import datetime, timedelta

class TTLCache: 
    
    def __init__(self, ttl):
        self.store = {}
        self.ttl = ttl
        self.lock = threading.RLock()
        
    def get(self, key):
        with self.lock:
            if key not in self.store:
                return (None, False)

            value, exp = self.store[key]
            if datetime.now() > exp:
                self.delete(key)
                return (None, False)
            return (value, True)
    
    def set(self, key, value):
        with self.lock:
            self.store[key] = (value, datetime.now() + timedelta(seconds = self.ttl))
        
    def delete(self, key):
        with self.lock:
            self.store.pop(key, None)
        
    def size(self):
        return len(self.store)