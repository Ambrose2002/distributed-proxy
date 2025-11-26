#!/bin/bash
cd "$(dirname "$0")"

# Kill using recorded PIDs if they exist
if [ -f .cluster_pids ]; then
    while read pid; do
        kill $pid 2>/dev/null
    done < .cluster_pids
    rm .cluster_pids
else
    echo "No PID file found. Attempting full kill anyway..."
fi

# Hard kill any leftover processes
pkill -f proxy_node.py 2>/dev/null
pkill -f origin_server.py 2>/dev/null
pkill -f load_balancer.py 2>/dev/null

echo "Cluster stopped."