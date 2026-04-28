#!/bin/bash
cd ~/echo-iris/software
while true; do
    python3 echo_iris_16gb.py "$@"
    echo ""
    echo "IRIS stopped. Press Enter to restart, Ctrl+C to quit."
    read -r || break
done
