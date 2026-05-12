#!/bin/bash

# Blackshot IoT Studio - Master Launcher
# -------------------------------------

echo "🎨 Initializing Blackshot IoT Studio..."

# 1. Build project
mkdir -p build
cd build
cmake ..
make -j$(nproc)
cd ..

if [ ! -f "build/BlackshotUISDK" ]; then
    echo "❌ Build failed. Check errors above."
    exit 1
fi

echo "✅ Build Complete."

# 2. Start Frontend Server (Background)
echo "🌐 Starting Frontend Server (Studio UI)..."
python3 -m http.server 8080 --directory studio &
HTTP_PID=$!

# 3. Start Studio Bridge
echo "🌉 Connecting Bridge..."
cd studio
python3 bridge.py

# Cleanup on exit
trap "kill $HTTP_PID; exit" INT TERM
