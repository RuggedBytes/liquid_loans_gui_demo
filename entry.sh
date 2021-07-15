#!/usr/bin/env bash
set -e

/root/elements/src/elementsd -datadir=/root/elementsdir1 -reindex `cat /root/demo_assets.txt`
/root/elements/src/elementsd -datadir=/root/elementsdir2 -reindex `cat /root/demo_assets.txt`

# wait for demons to start
sleep 6
export LD_LIBRARY_PATH=/usr/local/lib
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
exec "$@"
