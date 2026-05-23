/* VgaRenderer.h — abstract VGA mode-13h emulation on SDL2 */
#pragma once
#include <SDL.h>
#include <array>
#include <cstdint>
#include <span>
#include <string>

namespace pe {

class VgaRenderer {
public:
    static constexpr int W = 320;
    static constexpr int H = 200;

    VgaRenderer(int scale = 2, const std::string &title = "Planet's Edge (native)");
    ~VgaRenderer();

    VgaRenderer(const VgaRenderer &) = delete;
    VgaRenderer &operator=(const VgaRenderer &) = delete;

    /** Load 256-color palette from 768-byte VGA 6-bit RGB blob */
    void loadPalette(std::span<const uint8_t> palette768);

    /** Blit 320×200 indexed pixels into framebuffer */
    void blitFullscreen(std::span<const uint8_t> pixels64000);

    /** Direct access to 320x200 indexed pixel buffer for overlay drawing */
    uint8_t *indexedPixels() { return indexed_.data(); }
    const uint8_t *indexedPixels() const { return indexed_.data(); }

    /** Re-render indexed buffer to ARGB framebuffer (call after overlay draws) */
    void refresh();

    /** Present framebuffer to window */
    void present();

    /** Save current window content as BMP (for headless testing) */
    bool saveScreenshot(const std::string &path);

    /** Poll input events. Returns false if user requested quit. */
    bool pollEvents();

    bool keyPressed() const { return key_pressed_; }
    void resetKeyState() { key_pressed_ = false; }

private:
    SDL_Window   *win_ = nullptr;
    SDL_Renderer *ren_ = nullptr;
    SDL_Texture  *tex_ = nullptr;
    int scale_;
    bool key_pressed_ = false;

    std::array<uint32_t, 256> argb_palette_{};
    std::array<uint8_t, W * H>  indexed_{};
    std::array<uint32_t, W * H> framebuffer_{};
};

} // namespace pe
