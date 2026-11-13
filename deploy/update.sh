#!/bin/bash
# Run by systemd before each start: wait for the network, then pull the latest code.
# Never fails the service - an old checkout is better than no heater control.
cd "$(dirname "$0")/.." || exit 0
for i in $(seq 1 60); do
    getent hosts github.com >/dev/null 2>&1 && break
    sleep 2
done
git pull --ff-only || echo "git pull failed, running existing code"
exit 0
