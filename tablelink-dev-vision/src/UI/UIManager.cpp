#include "UIManager.h"
#include "DashboardView.h"

namespace UI {

void UIManager::init(int width, int height, int win_x, int win_y, bool borderless) {
    lv_init();
    
    // Iniciar subsistema SDL
    disp = lv_sdl_window_create(width, height);
    
    SDL_Window* win = SDL_GetWindowFromID(1);
    if (win) {
        if (win_x != SDL_WINDOWPOS_UNDEFINED && win_y != SDL_WINDOWPOS_UNDEFINED) {
            SDL_SetWindowPosition(win, win_x, win_y);
        }
        if (borderless) {
            SDL_SetWindowBordered(win, SDL_FALSE);
        }
    }

    mouse = lv_sdl_mouse_create();
    
    // Inicializar estilos y pantallas
    DashboardView::init_styles();
    lv_obj_t* screen = lv_screen_active();
    DashboardView::setup_screen(screen);

    running = true;
}

void UIManager::update() {
    if (!running) return;
    
    // En el futuro: Consumir el EventBus para parsear UI actions desde WebSockets.
    // Actualmente se hará en main.cpp para delegación clara, pero el tick gráfico va aquí:

    lv_timer_handler();
    
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_QUIT) {
            running = false;
        }
    }
}

} // namespace UI
