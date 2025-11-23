import threading
from datetime import datetime, timedelta

class TTLCache: 
    
    def __init__(self, ttl):
        self.store = {}
        self.ttl = ttl
        self.lock = threading.Lock()
        
    def get(self, key):
        self.lock.acquire()
        if key not in self.store:
            return (None, False)

        value, exp = self.store[key]
        if datetime.now() > exp:
            return (None, False)
        return (value, True)
    
    def set(self, key, value):
        self.lock.acquire()
        self.store[key] = (value, datetime.now() + timedelta(seconds = 180))
        
    def delete(self, key):
        self.lock.acquire()
        self.store.pop(key)
        
    def size(self):
        return len(self.store)