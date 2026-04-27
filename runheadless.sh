#!/bin/bash
# Launches Isaac Sim headless and loads this project's extension folder.
# Usage (inside the Isaac Sim docker container):
#   ./runheadless.sh --ext-folder /root/isaac-drone-inspection/extensions

ISAAC_SIM_DIR="${ISAAC_SIM_DIR:-/isaac-sim}"

"$ISAAC_SIM_DIR/runheadless.sh" \
    --ext-folder "$(dirname "$0")/extensions" \
    --enable isaac_drone_inspection \
    "$@"
