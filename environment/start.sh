#!/usr/bin/env bash
set -e

echo "[startup] fixing permissions..."

chown -R claude-user:claude-user /root/capsule/.claude
# chown -R claude-user:claude-user /root/capsule/scratch
# chown -R claude-user:claude-user /root/capsule/code
# chown -R claude-user:claude-user /root/capsule/results

#chmod -R o+w /root/capsule/.claude
chmod -R a+wX /scratch
chmod -R a+wX /root/capsule/code
chmod -R a+wX /results
chmod o+rx /root/capsule/data
