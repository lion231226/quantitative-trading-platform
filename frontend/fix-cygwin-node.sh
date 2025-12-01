#!/bin/bash

# Cygwin Node.js Environment Fix
# This script sets up aliases and functions to fix Node.js execution in Cygwin

# Function to run Node.js with proper Windows path handling
node() {
    "/c/Program Files/nodejs/node" "$@"
}

# Function to run npm with proper Windows path handling
npm() {
    "/c/Program Files/nodejs/npm" "$@"
}

# Function to run npx with proper Windows path handling
npx() {
    "/c/Program Files/nodejs/npx" "$@"
}

# Function to run Jest specifically
jest() {
    local project_dir="$(pwd)"
    local jest_path="$project_dir/node_modules/jest/bin/jest.js"
    "/c/Program Files/nodejs/node" "$jest_path" "$@"
}

# Export functions
export -f node npm npx jest

echo "✅ Cygwin Node.js environment fix applied"
echo "Available commands: node, npm, npx, jest"