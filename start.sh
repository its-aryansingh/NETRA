#!/bin/sh
set -e
echo "Starting NETRA Cockpit on Railpack / Railway..."
cd frontend
if [ ! -d "node_modules" ] || [ ! -d ".next" ]; then
  echo "Installing frontend dependencies and building..."
  npm install
  npm run build
fi
echo "Launching Next.js server on port ${PORT:-3000}..."
exec npx next start -H 0.0.0.0 -p "${PORT:-3000}"
