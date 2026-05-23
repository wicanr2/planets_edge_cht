#!/bin/bash
# Build C++17 SDL2 intro viewer + test against Intro.cc directly
set -eu
cd /mnt/d/03_tools/poc/sdl2_spike

# Need GCC with C++20 std::span (or C++17 + manual span). gcc 11.4 in 22.04 has span.
# Use C++20 to avoid header issues.
mkdir -p build_cpp
g++ -std=c++20 -O2 -Wall -Wextra \
    src/main.cpp src/VgaRenderer.cpp src/CcArchive.cpp src/Lzw.cpp \
    $(sdl2-config --cflags --libs) \
    -o build_cpp/pe_intro_viewer

ls -lh build_cpp/pe_intro_viewer
echo ""
file build_cpp/pe_intro_viewer
echo ""

# Headless test
TMP=$(mktemp -d)
trap "rm -rf $TMP; kill 0 2>/dev/null; true" EXIT INT TERM

DISP=99
while [ -e "/tmp/.X${DISP}-lock" ]; do DISP=$((DISP + 1)); done
Xvfb :$DISP -screen 0 800x600x24 -nolisten tcp >$TMP/xvfb.log 2>&1 &
XVFB_PID=$!
export DISPLAY=:$DISP
for i in $(seq 1 20); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.2; done

INTRO_CC="/mnt/d/03_game_tmp/1992_天際寒星_Planets Edge/PE/Intro.cc"

echo "=== render NEW WORLD COMPUTING splash via direct cc archive load ==="
timeout 4 ./build_cpp/pe_intro_viewer "$INTRO_CC" \
    --frame-id 4413 --palette-id EBC8 \
    --screenshot /tmp/cpp_4413.bmp || true

if [ -f /tmp/cpp_4413.bmp ]; then
    convert /tmp/cpp_4413.bmp /mnt/d/03_tools/poc/sdl2_spike/cpp_4413.png
    echo "  -> /mnt/d/03_tools/poc/sdl2_spike/cpp_4413.png"
    stat -c'    size=%s bytes' /mnt/d/03_tools/poc/sdl2_spike/cpp_4413.png
fi

echo ""
echo "=== render starfield ==="
timeout 4 ./build_cpp/pe_intro_viewer "$INTRO_CC" \
    --frame-id 5E5C --palette-id EBC8 \
    --screenshot /tmp/cpp_5E5C.bmp || true
if [ -f /tmp/cpp_5E5C.bmp ]; then
    convert /tmp/cpp_5E5C.bmp /mnt/d/03_tools/poc/sdl2_spike/cpp_5E5C.png
    echo "  -> /mnt/d/03_tools/poc/sdl2_spike/cpp_5E5C.png"
fi

kill $XVFB_PID 2>/dev/null
echo ""
echo "=== diff vs Phase A C version ==="
ls -la /mnt/d/03_tools/poc/sdl2_spike/pe_intro_viewer 2>/dev/null
ls -la /mnt/d/03_tools/poc/sdl2_spike/build_cpp/pe_intro_viewer
