#!/bin/bash
PORT=50000

source ~/miniconda3/etc/profile.d/conda.sh
conda activate funding-statement-generator

bokeh serve main.py --port $PORT \
--allow-websocket-origin localhost:$PORT \
--allow-websocket-origin $(hostname):$PORT \
--allow-websocket-origin $(hostname).local:$PORT \
#--allow-websocket-origin <your IP here>:$PORT \
