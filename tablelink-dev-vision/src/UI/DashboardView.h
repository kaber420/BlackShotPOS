#ifndef BS_DASHBOARD_VIEW_H
#define BS_DASHBOARD_VIEW_H

#include "lvgl.h"
#include "../ui/themes.h"
#include <vector>
#include <string>
#include <map>

namespace UI {

struct DishItem {
    int id;                         
    std::string name;
    int quantity;
    bool is_modified;
    std::string modification_notes;
    std::string status = "EN COLA"; 
    int progress = 0;               
};

// Widgets que representan UNA SOLA tarjeta de platillo
struct DishCardWidgets {
    lv_obj_t* card;
    lv_obj_t* status_label;
    lv_obj_t* status_cont;
    lv_obj_t* dot;
    int order_id;
};

class DashboardView {
public:
    static void init_styles();
    static void setup_screen(lv_obj_t* parent);
    static void add_order(const char* title, const std::vector<DishItem>& items, int order_id);

    static void update_item_status(int order_id, int item_id, int progress, const char* status);
    static void update_order_progress(int order_id, int percentage, const char* status);
    static void remove_order(int order_id); // Elimina todos los platos de esa orden
    static void remove_dish(int item_id);   // Elimina un plato específico

    static bool has_order(int order_id);
    static void clear_orders();

    static void set_connection_status(int status); 
    static void set_offline_mode(bool offline);

    static void update_business_name(const std::string& name);
    static void update_table_id(const std::string& id);

    static void show_goodbye_screen();

private:
    static lv_obj_t* screen;
    static lv_obj_t* header;
    static lv_obj_t* clock_label;
    static lv_obj_t* business_label;
    static lv_obj_t* table_id_label;
    static lv_obj_t* order_id_label;
    static lv_obj_t* tablepad_cont;
    static lv_obj_t* footer;
    static lv_obj_t* sidebar;      // Nuevo: Columna lateral para modo modern
    static lv_obj_t* main_content; // Nuevo: Área principal para modo modern
    static lv_obj_t* status_led;
    static lv_obj_t* offline_cont;
    static lv_obj_t* goodbye_overlay;

    // Métodos de Layout Modular
    static void setup_classic_list(lv_obj_t* parent);
    static void setup_modern_dashboard(lv_obj_t* parent);

    // Nuevo mapeo: item_id (ID único del platillo) -> Widgets de su tarjeta
    static std::map<int, DishCardWidgets> active_dish_cards;

    static bool bill_requested;

    // Crea una tarjeta individual para un platillo
    static lv_obj_t* create_dish_card(lv_obj_t* parent, const DishItem& dish, int order_id, const char* table_name);

    static void apply_item_state(DishCardWidgets& w, const char* status);

    static lv_style_t style_card;
    static lv_style_t style_btn;
    static lv_style_t style_text_small;
    static lv_style_t style_badge;
    static lv_style_t style_btn_icon;
    static lv_style_t style_item_badge;
    static lv_style_t style_mod_badge; // Estilo para complementos/modificaciones
};

} // namespace UI

#endif // BS_DASHBOARD_VIEW_H
