#include <iostream>
#include <string>
#include <thread>
#include <ArduinoJson.h>
#include <SDL2/SDL.h>

#include "UI/UIManager.h"
#include "UI/DashboardView.h"
#include "Network/SocketController.h"
#include "State/EventBus.h"
#include "State/AppState.h"


void studio_command_listener() {
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line == "FAULT:OFFLINE") {
            State::AppState::set_force_offline_fault(true);
            std::cout << "[STUDIO_ACK] Fault Injected: Offline" << std::endl;
        } else if (line == "FAULT:ONLINE") {
            State::AppState::set_force_offline_fault(false);
            std::cout << "[STUDIO_ACK] Fault Cleared: Online" << std::endl;
        } else if (line.find("CMD:MOVE ") == 0) {
            int x, y;
            if (sscanf(line.c_str(), "CMD:MOVE %d %d", &x, &y) == 2) {
                SDL_Window* win = SDL_GetWindowFromID(1);
                if (win) SDL_SetWindowPosition(win, x, y);
            }
        } else if (line == "CMD:PING") {
            std::cout << "[STUDIO_ACK] PONG" << std::endl;
        }
    }
}

int main(int argc, char** argv) {
    std::string token = "test-token-123";
    std::string host = "localhost:8400";
    int win_x = SDL_WINDOWPOS_UNDEFINED;
    int win_y = SDL_WINDOWPOS_UNDEFINED;
    bool borderless = false;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--token" && i + 1 < argc) token = argv[++i];
        else if (arg == "--host" && i + 1 < argc) host = argv[++i];
        else if (arg == "--x" && i + 1 < argc) win_x = std::stoi(argv[++i]);
        else if (arg == "--y" && i + 1 < argc) win_y = std::stoi(argv[++i]);
        else if (arg == "--table" && i + 1 < argc) State::AppState::set_table_id(argv[++i]);
        else if (arg == "--borderless") borderless = true;
    }

    // 1. Iniciar hilo de comandos de Studio
    std::thread(studio_command_listener).detach();

    // 2. Inicializar la UI (Core 1 simulado)
    UI::UIManager::get_instance().init(SCREEN_WIDTH, SCREEN_HEIGHT, win_x, win_y, borderless);

    // 3. Inicializar la Red (Core 0 simulado dentro de SocketController)
    Network::SocketController::get_instance().init(host, token);
    Network::SocketController::get_instance().start();

    // Registrar tiempo inicial
    State::AppState::set_last_connected_time(SDL_GetTicks());

    std::string raw_msg;
    
    // 4. Bucle Principal "RTOS Task" (Sincronización y UI)
    while (UI::UIManager::get_instance().is_running()) {
        uint32_t now = SDL_GetTicks();
        
        // --- 1. WATCHDOG DE CONEXIÓN (Cada 5 segundos) ---
        static uint32_t last_check = 0;
        if (now - last_check > 5000) {
            if (State::AppState::is_force_offline_fault()) {
                if (State::AppState::get_connection_status() != State::ConnectionStatus::DISCONNECTED) {
                    std::cout << "[STUDIO] Injecting Network Failure..." << std::endl;
                    Network::SocketController::get_instance().stop();
                    UI::DashboardView::set_connection_status(0);
                    UI::DashboardView::set_offline_mode(true);
                    State::AppState::set_offline_mode(true);
                    State::AppState::set_connection_status(State::ConnectionStatus::DISCONNECTED);
                }
            } else if (State::AppState::get_connection_status() != State::ConnectionStatus::CONNECTED) {
                if (now - State::AppState::get_last_connected_time() > 45000) {
                    std::cout << "🔄 [WATCHDOG] Connection Timeout. Restarting..." << std::endl;
                    Network::SocketController::get_instance().stop();
                    Network::SocketController::get_instance().start();
                    State::AppState::set_last_connected_time(now);
                    UI::DashboardView::set_connection_status(1);
                    State::AppState::set_connection_status(State::ConnectionStatus::CONNECTING);
                }
            } else {
                State::AppState::set_last_connected_time(now);
            }
            last_check = now;
        }

        // --- 2. PROCESAMIENTO DE MENSAJES (TIEMPO REAL) ---
        // Helpers de parsing robustos para ArduinoJson
        auto parse_int = [](JsonVariant j, const char* key, int def = 0) -> int {
            if (!j.containsKey(key) || j[key].isNull()) return def;
            if (j[key].is<int>()) return j[key].as<int>();
            if (j[key].is<const char*>()) {
                try { return std::stoi(j[key].as<const char*>()); } catch (...) { return def; }
            }
            return def;
        };

        auto parse_status = [&](JsonVariant payload, JsonVariant item) -> std::string {
            // Prioridad 1: item_status (específico del platillo)
            if (payload.containsKey("item_status") && !payload["item_status"].isNull()) 
                return payload["item_status"].as<const char*>();
            
            // Prioridad 2: status en el payload
            if (payload.containsKey("status") && !payload["status"].isNull()) 
                return payload["status"].as<const char*>();
            
            // Prioridad 3: status en el objeto raíz (item)
            if (item.containsKey("status") && !item["status"].isNull())
                return item["status"].as<const char*>();

            return "PREPARANDO"; 
        };

        auto process_msg = [&](JsonVariant doc) {
            std::function<void(JsonVariant)> unwrap = [&](JsonVariant item) {
                if (item.is<JsonArray>()) {
                    for (JsonVariant i : item.as<JsonArray>()) unwrap(i);
                    return;
                }

                const char* event_cstr = item["event"] | "";
                std::string event = event_cstr;
                
                // Desenvolver capas anidadas
                if (event == "" && item.containsKey("data") && item["data"].is<JsonObject>()) {
                    unwrap(item["data"]);
                    return;
                }
                if (item.containsKey("topic") && item.containsKey("data")) {
                    unwrap(item["data"]);
                    return;
                }

                JsonVariant payload = item["data"];
                if (payload.isNull()) payload = item;

                if (event == "internal_conn") {
                    int st = item["status"] | 0; 
                    if (st == 2) {
                        State::AppState::set_last_connected_time(SDL_GetTicks());
                        UI::DashboardView::set_connection_status(2);
                        UI::DashboardView::set_offline_mode(false);
                        State::AppState::set_connection_status(State::ConnectionStatus::CONNECTED);
                    } else if (st == 0) {
                        UI::DashboardView::set_connection_status(0);
                        State::AppState::set_connection_status(State::ConnectionStatus::DISCONNECTED);
                    }
                    return;
                }

                if (event == "config") {
                    const char* bname = payload["business_name"] | "BLACKSHOT";
                    State::AppState::set_business_name(bname);
                    UI::DashboardView::update_business_name(bname);
                    
                    if (payload.containsKey("table_id")) {
                        std::string tid;
                        if (payload["table_id"].is<int>()) 
                            tid = std::to_string(payload["table_id"].as<int>());
                        else 
                            tid = payload["table_id"].as<const char*>() ? payload["table_id"].as<const char*>() : "0";
                        
                        State::AppState::set_table_id(tid);
                        UI::DashboardView::update_table_id(tid);
                    }
                    State::EventBus::push_ui_action({"sync_orders", ""});
                    return;
                }

                if (event == "pong") return;

                // Limpieza de mesa: el POS notifica que la mesa fue cobrada/liberada
                if (event == "clear_table" || event == "table_cleared") {
                    std::cout << "🧹 [PARSER]: Mesa liberada → limpiando pantalla y restableciendo botones." << std::endl;
                    UI::DashboardView::clear_orders();
                    UI::DashboardView::reset_waiter_button();
                    UI::DashboardView::reset_bill_button();
                    return;
                }

                // Solicitudes atendidas: el mesero limpió las alertas en el POS
                if (event == "clear_requests") {
                    std::cout << "🛎️ [PARSER]: Solicitudes atendidas → restableciendo botones." << std::endl;
                    UI::DashboardView::reset_waiter_button();
                    UI::DashboardView::reset_bill_button();
                    return;
                }

                // Alternativa: una orden específica fue entregada
                if (event == "order_delivered") {
                    int order_id = payload["order_id"] | (int)item["order_id"] | 0;
                    std::cout << "✅ [PARSER]: Orden #" << order_id << " entregada." << std::endl;
                    UI::DashboardView::update_order_progress(order_id, 100, "ENTREGADO");
                    return;
                }

                if (event == "order_new" || (event == "" && item.containsKey("order_id"))) {
                    int order_id = parse_int(payload, "order_id", parse_int(item, "order_id", 0));
                    std::string title = "Mesa " + State::AppState::get_table_id();
                    std::vector<UI::DishItem> dishes;
                    
                    JsonArray itms = payload["items"].as<JsonArray>();
                    if (itms.isNull()) itms = item["items"].as<JsonArray>();

                    for (JsonObject d : itms) {
                        int dish_id = parse_int(d, "id", parse_int(d, "item_id", 0));

                        dishes.push_back({
                            dish_id,
                            d["name"] | "Item", 
                            d["qty"] | 1, 
                            d["mod"] | false, 
                            d["notes"] | "",
                            d["status"] | "EN COLA"
                        });
                    }

                    std::cout << "✅ [PARSER]: Nueva Orden ID: " << order_id << " con " << dishes.size() << " platillos." << std::endl;
                    UI::DashboardView::add_order(title.c_str(), dishes, order_id);
                    
                    lv_obj_invalidate(lv_scr_act());
                    return;
                }

                if (event == "order_update") {
                    int order_id = parse_int(payload, "order_id", parse_int(item, "order_id", 0));
                    std::string st = parse_status(payload, item);
                    int prog = payload["progress"] | (int)item["progress"] | 0;

                    if (!UI::DashboardView::has_order(order_id)) {
                        std::cout << "⚠️  [PARSER]: order_update sin orden previa ID: " << order_id << " → sync" << std::endl;
                        State::EventBus::push_ui_action({"sync_orders", ""});
                    } else {
                        // Intentar obtener item_id con ambos nombres posibles
                        int item_id = parse_int(payload, "item_id", parse_int(item, "item_id", 
                                       parse_int(payload, "id", parse_int(item, "id", 0))));

                        if (item_id > 0) {
                            // Actualización de PLATILLO individual
                            std::cout << "✅ [PARSER]: Platillo ID " << item_id << " de orden " << order_id << " → " << st << std::endl;
                            UI::DashboardView::update_item_status(order_id, item_id, prog, st.c_str());
                        } else {
                            // Actualización de TODA la orden
                            std::cout << "✅ [PARSER]: Orden completa ID: " << order_id << " → " << st << std::endl;
                            UI::DashboardView::update_order_progress(order_id, prog, st.c_str());
                        }
                    }
                    lv_obj_invalidate(lv_scr_act());
                    return;
                }
            };
            unwrap(doc);
        };

        while (State::EventBus::pop_network_message(raw_msg)) {
            std::cout << "📡 [RAW RECEIVE]: " << raw_msg << std::endl;
            
            JsonDocument doc;
            DeserializationError error = deserializeJson(doc, raw_msg);
            
            if (error) {
                std::cerr << "❌ [JSON ERROR]: " << error.c_str() << std::endl;
            } else {
                process_msg(doc.as<JsonVariant>());
            }
        }

        // --- 3. ACTUALIZACIÓN DE HILOS SIMULADOS ---
        Network::SocketController::get_instance().update();
        UI::UIManager::get_instance().update();

        SDL_Delay(5);
    }

    Network::SocketController::get_instance().stop();
    return 0;
}
