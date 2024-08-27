#!/usr/bin/with-contenv bashio
set -e

echo "Running Script BMS"

# cd "${0%/*}"
cd /workdir
python3 -u ./bms1.py #"$@"
