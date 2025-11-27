from proxy.cache_utils import LRUCache

def test_capacity():
    cache = LRUCache(3)
    assert cache.capacity == 3
    
def test_initial_size_is_zero():
    cache = LRUCache(3)
    assert cache.size() == 0
    

def test_set_basic():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    assert cache.size() == 1
    
    cache.set("key2", "value2")
    assert cache.size() == 2
    
def test_set_modify_existing_key():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    assert cache.size() == 1
    
    cache.set("key1", "value01")
    assert cache.size() == 1
    
def test_set_exceed_capacity():
    cache = LRUCache(2)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.size() == 2 
    
def test_get_basic():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    
    assert cache.get("key1")[0] == "value1"
    
def test_get_modified_key():
    cache = LRUCache(3)
    cache.set("key1", "value1")
    cache.set("key1", "value01")
    
    assert cache.get("key1")[0] == "value01"
    
def test_get_capacity_exceeded():
    cache = LRUCache(2)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.get("key1")[0] == None