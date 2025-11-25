#!/bin/bash

set -e

cd "$(dirname "$0")"

# configs
ORIGIN_PORT=8000
LB_PORT=9000
TTL=30
RB_STRATEGY="round_robin"
LL_STRATEGY="least_loaded"

rm -f .cluster_pids

# start origin server
echo "Starting server on $ORIGIN_PORT"
python origin/origin_server.py &
echo $! >> .cluster_pids
sleep 1

# start proxy nodes
for port in 8001 8002 8003; do 
    echo "Starting proxy on $port"
    python proxy/proxy_node.py --port $port --origin_port $ORIGIN_PORT --ttl $TTL &
    echo $! >> .cluster_pids
    sleep 1
done

# start load balancer
echo "Starting load balancer on $LB_PORT"
python load_balancer/load_balancer.py --port $LB_PORT --proxies 127.0.0.1:8001 127.0.0.1:8002 127.0.0.1:8003 --strategy $RB_STRATEGY &
echo $! >> .cluster_pids

echo "Cluster started!"