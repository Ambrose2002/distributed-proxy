# Distributed Proxy System — Design Document

This project implements a simple distributed caching system consisting of:
1. An **origin server** that stores data files.
2. Multiple **proxy nodes** that provide TTL-based caching.
3. A **load balancer** that distributes incoming client requests.
4. A **client** used to send test GET and METRICS requests.

The goal of the design is to practice distributed systems concepts such as concurrency, caching, load balancing, health checks, and failure handling.

---

## 1. Origin Server

**Purpose:**  
Serves as the single source of truth for all data.  
It handles only simple GET requests of the form:

```
GET resource/key
```

**Behavior:**
- Looks up `data/resourcekey.json` on disk.
- Returns a JSON response:
  - `{"status": "OK", "data": {...}}`
  - or `{"status": "NOT_FOUND", "data": null}`
- Sends exactly **one newline-terminated JSON line** per request.

---

## 2. Proxy Node

**Purpose:**  
Acts as a caching layer that reduces load on the origin server.  
The cache type is selectable via the `--cache_type` argument (`ttl` or `lru`).

**Key Components:**
- **Cache Layer:** Supports two interchangeable cache types:
  - TTLCache: key → (value, expiration timestamp)
  - LRUCache: key → value with least-recently-used eviction
- **Metrics:** Tracks hits, misses, requests, and origin fetches.
- **TCP Server:** Handles client requests concurrently using threads.

**Behavior:**
- Accepts `GET resource/key` from the load balancer.
- If cached and valid → returns cached value.
- If not cached → fetches from origin, caches it, returns it.
- Responds with:
  - `{"status": "...", "data": ..., "cache_hit": bool, "node": port}`

**Metrics Endpoint:**  
If it receives `METRICS`, it returns a metrics dictionary instead of data.

---

## 3. Load Balancer

**Purpose:**  
Distributes incoming client traffic across proxy nodes.

**Features:**
- Two strategies:
  - **round_robin**
  - **least_loaded**
- Periodic health checks and metrics polling for every proxy.
- Forwards requests and returns responses to clients.
- Provides a client-facing `METRICS` endpoint summarizing cluster state.

**Failure Handling:**
- If a proxy cannot be reached or returns bad data, it is marked unhealthy.
- Only healthy proxies are used for routing decisions.

---

## 4. Node Manager

**Purpose:**  
Tracks proxy health and implements simple failure thresholds.

**Behavior:**
- Each failed request increments a failure count.
- After exceeding a threshold, a proxy is marked unhealthy.
- Provides lists of healthy nodes for the load balancer.

---

## 5. Client

**Purpose:**  
Simple utility for interacting with the load balancer.

**Commands:**
- `--get path` → issues a GET request.
- `--metrics` → requests system metrics from the load balancer.

**Behavior:**
- Prints the JSON response.
- Operates over a single TCP request/response per invocation.

---

## 6. Request/Response Protocol

Across all components, messages follow the same rules:

- Each request is a **single line** ending with `\n`.
- Each response is a **single JSON object** ending with `\n`.
- No connection reuse; every request uses one TCP connection.

This avoids partial reads and simplifies framing.

---

## 7. Concurrency Model

- Proxy nodes and load balancer use **thread-per-connection**.
- Shared structures (cache, health state) use thread-safe locking.
- The metrics polling loop runs as a background daemon thread.

---

## 8. Running the System

**Start Origin:**
```
python origin/origin_server.py
```

**Start Proxies:**
```
python proxy/proxy_node.py --port 8001 --origin_port 8000 --cache_type ttl
python proxy/proxy_node.py --port 8002 --origin_port 8000 --cache_type ttl
python proxy/proxy_node.py --port 8003 --origin_port 8000 --cache_type ttl
```

**Start Load Balancer:**
```
python load_balancer/load_balancer.py --port 9000 --proxies 127.0.0.1:8001 127.0.0.1:8002 127.0.0.1:8003
```

**Make Requests:**
```
python client/client.py --port 9000 --get article/1
python client/client.py --port 9000 --metrics
```

### Cache Type Options

```
--cache_type ttl   # default TTL-based caching
--cache_type lru   # LRU caching with eviction policy
```

---

## 9. Summary

This system demonstrates core distributed-system concepts through a clean, minimal architecture:

- Origin → Proxies (caching) → Load Balancer → Client  
- Health checks  
- Failover and request routing  
- Pluggable caching strategies (TTL or LRU)  
- Cluster-wide metrics reporting  

Simple, predictable behaviors make the system easy to extend or modify while maintaining clarity.
