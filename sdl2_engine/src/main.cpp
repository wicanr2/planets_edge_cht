/* PE native intro viewer — C++17 + SDL2 + Big5 subtitle overlay
 *
 * Loads a 64000-byte frame from a .cc archive, overlays a Big5 (cp950)
 * subtitle string from the loaded font blob, renders to SDL2.
 *
 * Usage:
 *   pe_intro_viewer <Intro.cc> [--frame-id HEX] [--palette-id HEX]
 *                              [--font big5_font_12.bin]
 *                              [--subtitle "..."]
 *                              [--screenshot OUT.bmp]
 */
#include "VgaRenderer.h"
#include "CcArchive.h"
#include "Big5Font.h"
#include "Subtitles.h"

#include <SDL.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>
#include <string>

static uint16_t parseHex(const char *s) {
    return static_cast<uint16_t>(std::strtoul(s, nullptr, 16));
}

/** Find subtitle by id; returns empty span if not found. */
static std::span<const uint8_t> lookupSubtitle(const std::string &id) {
    for (size_t i = 0; i < pe::kSubtitlesCount; i++) {
        if (id == pe::kSubtitles[i].id) {
            return std::span<const uint8_t>(pe::kSubtitles[i].big5_bytes,
                                            pe::kSubtitles[i].big5_len);
        }
    }
    return {};
}

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "usage: " << argv[0] << " <cc-archive> [options]\n";
        return 2;
    }

    std::string cc_path  = argv[1];
    uint16_t    frame_id = 0x4413;
    uint16_t    pal_id   = 0xEBC8;
    std::string snap;
    std::string font_path = "big5_font_12.bin";
    std::string subtitle_id = "nwc";
    int subtitle_y = 175;
    int subtitle_color = 15;

    for (int i = 2; i < argc; i++) {
        std::string a = argv[i];
        if      (a == "--frame-id"   && i + 1 < argc) frame_id   = parseHex(argv[++i]);
        else if (a == "--palette-id" && i + 1 < argc) pal_id     = parseHex(argv[++i]);
        else if (a == "--font"       && i + 1 < argc) font_path  = argv[++i];
        else if (a == "--subtitle"   && i + 1 < argc) subtitle_id = argv[++i];
        else if (a == "--subtitle-y" && i + 1 < argc) subtitle_y = std::atoi(argv[++i]);
        else if (a == "--subtitle-color" && i + 1 < argc) subtitle_color = std::atoi(argv[++i]);
        else if (a == "--screenshot" && i + 1 < argc) snap       = argv[++i];
    }

    try {
        pe::CcArchive cc(cc_path);
        auto frame = cc.getEntry(frame_id);
        auto pal   = cc.getEntry(pal_id);
        if (!frame || frame->size() != 64000) {
            std::cerr << "frame 0x" << std::hex << frame_id << " missing/wrong size\n"; return 1;
        }
        if (!pal || pal->size() != 768) {
            std::cerr << "palette 0x" << std::hex << pal_id << " missing/wrong size\n"; return 1;
        }

        pe::Big5Font font;
        if (!font.load(font_path)) {
            std::cerr << "warning: failed to load font (continuing without subtitle)\n";
        } else {
            std::cout << "loaded font: " << font.glyphCount() << " glyphs\n";
        }

        pe::VgaRenderer vga;
        vga.loadPalette(*pal);
        vga.blitFullscreen(*frame);

        /* Overlay subtitle (looked up by id from pre-encoded table) */
        if (font.glyphCount() > 0) {
            auto big5_bytes = lookupSubtitle(subtitle_id);
            if (big5_bytes.empty()) {
                std::cerr << "subtitle id '" << subtitle_id << "' not found\n";
            } else {
                std::cout << "subtitle '" << subtitle_id << "' = "
                          << big5_bytes.size() << " big5 bytes\n";

                /* Black backdrop for readability */
                uint8_t *px = vga.indexedPixels();
                int text_w = static_cast<int>(big5_bytes.size() / 2 * 12 + 4);
                int text_x = (320 - text_w) / 2;
                for (int yy = subtitle_y - 2; yy < subtitle_y + 14; yy++) {
                    if (yy < 0 || yy >= 200) continue;
                    for (int xx = text_x - 2; xx < text_x + text_w; xx++) {
                        if (xx < 0 || xx >= 320) continue;
                        px[yy * 320 + xx] = 0;
                    }
                }
                font.drawText(px, 320, 320, 200, text_x, subtitle_y,
                              big5_bytes, static_cast<uint8_t>(subtitle_color));
                vga.refresh();
            }
        }

        vga.present();

        Uint32 start = SDL_GetTicks();
        const Uint32 timeout_ms = snap.empty() ? 0u : 1500u;
        bool running = true;
        while (running) {
            running = vga.pollEvents();
            vga.present();
            if (timeout_ms && SDL_GetTicks() - start > timeout_ms) {
                vga.saveScreenshot(snap);
                std::cout << "saved " << snap << "\n";
                running = false;
            }
            SDL_Delay(16);
        }
    } catch (const std::exception &e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
