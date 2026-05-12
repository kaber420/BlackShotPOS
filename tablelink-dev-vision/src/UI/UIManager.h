#ifndef BS_UI_MANAGER_H
#define BS_UI_MANAGER_H

#include "lvgl.h"
#include <SDL2/SDL.h>

namespace UI {

class UIManager {
public:
    static UIManager& get_instance() {
        static UIManager instance;
        return instance;
    }

    void init(int width, int height, int win_x, int win_y, bool borderless);
    void update(); // Debe llamarse en el hilo principal (Core 1)
    bool is_running() const { return running; }
    void stop() { running = false; }

private:
    UIManager() : running(false) {}
    bool running;
    
    lv_display_t * disp;
    lv_indev_t * mouse;
};

} // namespace UI

#endif // BS_UI_MANAGER_H
