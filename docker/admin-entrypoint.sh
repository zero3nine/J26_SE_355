#!/bin/sh
set -eu

mkdir -p /app/data/logs /app/data/reports
if [ ! -e /app/data/approved_domains.txt ]; then
    cp /app/config/approved_domains.default.txt /app/data/approved_domains.txt
fi

exec "$@"
