from proxy.cache_utils import TTLCache
import time

def test_size():
    cache = TTLCache(3)
    assert cache.size() == 0
    
def test_set_basic():
    cache = TTLCache(3)
    cache.set("key1", "value1")
    assert cache.size() == 1
    
def test_get_basic():
    cache = TTLCache(3)
    cache.set("key1", "value1")
    assert cache.get("key1")[0] == "value1"
    
def test_get_modified():
    cache = TTLCache(3)
    cache.set("key1", "value1")
    cache.set("key1", "value01")
    assert cache.get("key1")[0] == "value01"
    
def test_get_after_ttl_expire():
    cache = TTLCache(1)
    cache.set("key1", "value1")
    time.sleep(2)
    assert cache.get("key1")[0] == None