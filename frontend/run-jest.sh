#!/bin/bash

# Jest runner wrapper for Cygwin environment
# This script fixes the Node.js path issues in Cygwin

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Convert Windows paths to Cygwin paths for Node.js
export NODE_PATH="/cygdrive/c/Program Files/nodejs/node_modules"

# Use Windows Node.js directly with proper path conversion
WIN_NODE="/cygdrive/c/Program Files/nodejs/node.exe"

# Change to the project directory
cd "$SCRIPT_DIR"

# Run Jest with Windows Node.js, converting paths back to Windows format
WIN_SCRIPT_DIR=$(cygpath -w "$SCRIPT_DIR")
cd "$WIN_SCRIPT_DIR" || cd "$SCRIPT_DIR"

# Execute Jest with proper environment
"$WIN_NODE" "$WIN_SCRIPT_DIR/node_modules/.bin/jest" "$@"