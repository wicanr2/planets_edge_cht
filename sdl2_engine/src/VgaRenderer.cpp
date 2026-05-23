#include "VgaRenderer.h"
#include <stdexcept>
#include <iostream>
#include <cstring>

namespace pe {

VgaRenderer::VgaRenderer(int scale, const std::string &title) : scale_(scale) {
    if (SDL_Init(SDL_INIT_VIDEO) < 0)
        throw std::runtime_error(std::string("SDL_Init: ") + SDL_GetError());

    win_ = SDL_CreateWindow(title.c_str(),
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        W * scale_, H * scale_, SDL_WINDOW_SHOWN);
    if (!win_) throw std::runtime_error(std::string("CreateWindow: ") + SDL_GetError());

    ren_ = SDL_CreateRenderer(win_, -1, SDL_RENDERER_ACCELERATED);
    if (!ren_) ren_ = SDL_CreateRenderer(win_, -1, SDL_RENDERER_SOFTWARE);
    if (!ren_) throw std::runtime_error(std::string("CreateRenderer: ") + SDL_GetError());

    tex_ = SDL_CreateTexture(ren_, SDL_PIXELFORMAT_ARGB8888,
                              SDL_TEXTUREACCESS_STREAMING, W, H);
    if (!tex_) throw std::runtime_error(std::string("CreateTexture: ") + SDL_GetError());

    for (int i = 0; i < 256; i++)
        argb_palette_[i] = 0xFF000000u | (i << 16) | (i << 8) | i;
}

VgaRenderer::~VgaRenderer() {
    if (tex_) SDL_DestroyTexture(tex_);
    if (ren_) SDL_DestroyRenderer(ren_);
    if (win_) SDL_DestroyWindow(win_);
    SDL_Quit();
}

void VgaRenderer::loadPalette(std::span<const uint8_t> p) {
    if (p.size() < 768)
        throw std::invalid_argument("palette must be 768 bytes");
    for (int i = 0; i < 256; i++) {
        uint8_t r6 = p[i * 3 + 0];
        uint8_t g6 = p[i * 3 + 1];
        uint8_t b6 = p[i * 3 + 2];
        uint8_t r = static_cast<uint8_t>((r6 << 2) | (r6 >> 4));
        uint8_t g = static_cast<uint8_t>((g6 << 2) | (g6 >> 4));
        uint8_t b = static_cast<uint8_t>((b6 << 2) | (b6 >> 4));
        argb_palette_[i] = 0xFF000000u | (r << 16) | (g << 8) | b;
    }
}

void VgaRenderer::blitFullscreen(std::span<const uint8_t> px) {
    if (px.size() < static_cast<size_t>(W * H))
        throw std::invalid_argument("pixels must be 64000 bytes");
    std::memcpy(indexed_.data(), px.data(), W * H);
    refresh();
}

void VgaRenderer::refresh() {
    for (int i = 0; i < W * H; i++)
        framebuffer_[i] = argb_palette_[indexed_[i]];
    SDL_UpdateTexture(tex_, nullptr, framebuffer_.data(), W * 4);
}

void VgaRenderer::present() {
    SDL_RenderClear(ren_);
    SDL_RenderCopy(ren_, tex_, nullptr, nullptr);
    SDL_RenderPresent(ren_);
}

bool VgaRenderer::saveScreenshot(const std::string &path) {
    SDL_Surface *s = SDL_CreateRGBSurfaceWithFormat(0, W * scale_, H * scale_, 32,
                                                     SDL_PIXELFORMAT_ARGB8888);
    if (!s) return false;
    SDL_RenderReadPixels(ren_, nullptr, SDL_PIXELFORMAT_ARGB8888, s->pixels, s->pitch);
    int rc = SDL_SaveBMP(s, path.c_str());
    SDL_FreeSurface(s);
    return rc == 0;
}

bool VgaRenderer::pollEvents() {
    SDL_Event ev;
    while (SDL_PollEvent(&ev)) {
        if (ev.type == SDL_QUIT) return false;
        if (ev.type == SDL_KEYDOWN) {
            key_pressed_ = true;
            if (ev.key.keysym.sym == SDLK_ESCAPE || ev.key.keysym.sym == SDLK_q)
                return false;
        }
    }
    return true;
}

} // namespace pe
