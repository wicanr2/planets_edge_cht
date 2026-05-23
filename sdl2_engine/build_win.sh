#!/bin/bash
# Cross-compile pe_intro_viewer for Windows via mingw-w64.
# Downloads SDL2 mingw devel package on first run.
set -eu
cd /mnt/d/03_tools/poc/sdl2_spike

SDL2_MINGW_VER=2.30.10
SDL2_MINGW_DIR="$HOME/sdl2-mingw-${SDL2_MINGW_VER}"

# Step 1: Download SDL2 mingw devel if needed
if [ ! -d "$SDL2_MINGW_DIR" ]; then
    echo "=== Downloading SDL2 ${SDL2_MINGW_VER} mingw devel ==="
    mkdir -p "$SDL2_MINGW_DIR"
    cd "$SDL2_MINGW_DIR"
    curl -fL -o sdl2.tar.gz \
        "https://github.com/libsdl-org/SDL/releases/download/release-${SDL2_MINGW_VER}/SDL2-devel-${SDL2_MINGW_VER}-mingw.tar.gz"
    ls -lh sdl2.tar.gz
    tar -xzf sdl2.tar.gz --strip-components=1
    ls
    cd /mnt/d/03_tools/poc/sdl2_spike
fi

# Step 2: Cross-compile for x86_64 Windows
SDL2_X86_64="$SDL2_MINGW_DIR/x86_64-w64-mingw32"
echo "=== Cross-compile pe_intro_viewer for Windows x86_64 ==="
echo "  SDL2 root: $SDL2_X86_64"
ls -d "$SDL2_X86_64/include/SDL2" "$SDL2_X86_64/lib"

mkdir -p build_win
# Regenerate subtitle header (Big5 pre-encoded; avoids runtime iconv)
python3 gen_subtitles.py >/dev/null
# Regenerate font blob (same on both platforms)
python3 gen_font.py >/dev/null

x86_64-w64-mingw32-g++ -std=c++20 -O2 -Wall \
    -static-libgcc -static-libstdc++ \
    -DSDL_MAIN_HANDLED \
    src/main.cpp src/VgaRenderer.cpp src/CcArchive.cpp src/Lzw.cpp src/Big5Font.cpp \
    -I"$SDL2_X86_64/include" -I"$SDL2_X86_64/include/SDL2" -Isrc \
    -L"$SDL2_X86_64/lib" \
    -lmingw32 -lSDL2main -lSDL2 \
    -o build_win/pe_intro_viewer.exe

echo ""
ls -lh build_win/pe_intro_viewer.exe
file build_win/pe_intro_viewer.exe

# Step 3: Bundle SDL2.dll
echo ""
echo "=== Bundling SDL2.dll + assets ==="
cp -f "$SDL2_X86_64/bin/SDL2.dll" build_win/
ls -lh build_win/

# Make a Windows-runnable package dir
PKG=/mnt/d/03_tools/poc/sdl2_spike/win_package
mkdir -p "$PKG"
cp -f build_win/pe_intro_viewer.exe "$PKG/"
cp -f build_win/SDL2.dll            "$PKG/"
cp -f big5_font_12.bin              "$PKG/"
# include a sample cc archive locally so it works without game install
cp -f "/mnt/d/03_game_tmp/1992_天際寒星_Planets Edge/PE/Intro.cc" "$PKG/" 2>/dev/null || \
    echo "  (cannot copy game data — IP-protected; user must supply)"

# Add a run.bat
cat > "$PKG/run.bat" <<'BAT'
@echo off
pe_intro_viewer.exe Intro.cc --frame-id 4413 --palette-id EBC8 --font big5_font_12.bin --subtitle nwc
BAT

ls -lh "$PKG/"
echo ""
echo "Package ready at: $PKG"
