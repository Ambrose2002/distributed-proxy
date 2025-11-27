# Distributed Proxy System

A simple distributed caching system built to practice core distributed systems concepts such as load balancing, caching, concurrency, health checks, and failure handling. The system consists of:

1. **Origin Server** – the source of truth for data.
2. **Proxy Nodes** – cache data using TTL-based expiration.
3. **Load Balancer** – distributes client requests across proxies.
4. **Client** – sends GET and METRICS requests to the load balancer.

---

## Features

- TTL-based caching at each proxy.
- Round-robin or least-loaded load balancing.
- Health checks and automatic failure detection.
- Metrics reporting from proxies and the load balancer.
- Simple newline‑terminated JSON request/response protocol.
- Support for multiple cache types (TTLCache and LRUCache) configurable per proxy.

---

## Cache Types

- `--cache_type ttl` (default TTL-based cache)
- `--cache_type lru` (LRU cache with configurable capacity)

---

## Running the System

### 1. Start the Origin Server
```
python origin/origin_server.py
```

### 2. Start Proxy Nodes
```
python proxy/proxy_node.py --port 8001 --origin_port 8000 --cache_type lru
python proxy/proxy_node.py --port 8002 --origin_port 8000 --cache_type lru
python proxy/proxy_node.py --port 8003 --origin_port 8000 --cache_type lru
```

### 3. Start the Load Balancer
```
python load_balancer/load_balancer.py --port 9000 --proxies 127.0.0.1:8001 127.0.0.1:8002 127.0.0.1:8003
```

---

## Using the Client

### GET a resource
```
python client/client.py --port 9000 --get article/1
```

### View cluster metrics
```
python client/client.py --port 9000 --metrics
```

---

## Using the Cluster Scripts

To easily start and stop the full distributed system, use the provided scripts in the `scripts/` directory.

### Start the full cluster
```
./scripts/start_cluster.sh
```

This launches:
- Origin server  
- All proxy nodes (started with LRUCache by default)  
- Load balancer  

Proxies are started with the provided cache type via start_cluster.sh.

### Stop the full cluster
```
./scripts/kill_cluster.sh
```

This safely terminates all running components using both tracked PIDs and process-name matching.

---

## Project Structure

```
origin/         - origin server and data files
proxy/          - proxy node, cache, metrics
load_balancer/  - load balancer + node manager
client/         - client CLI
```

---

## Summary

This project demonstrates a clean and minimal implementation of distributed caching with clear separation between origin, proxies, load balancer, and client.
