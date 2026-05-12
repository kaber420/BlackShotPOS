#include "SocketController.h"
#include "../State/EventBus.h"
#include "../State/AppState.h"
#include <iostream>
#include <ArduinoJson.h>
#include <SDL2/SDL.h>

namespace Network {

void SocketController::init(const std::string& host, const std::string& token) {
    ws_url = "ws://" + host + "/api/v1/pos/ws/iot?token=" + token;
    webSocket.setUrl(ws_url);

    webSocket.enableAutomaticReconnection();
    webSocket.setPingInterval(30);

    webSocket.setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
        this->on_message(msg);
    });
}

void SocketController::on_message(const ix::WebSocketMessagePtr& msg) {
    if (msg->type == ix::WebSocketMessageType::Message) {
        State::EventBus::push_network_message(msg->str);
    } else if (msg->type == ix::WebSocketMessageType::Open) {
        std::cout << "🚀 [SOCKET] Handshake: Connection opened. Sending ID and Sync..." << std::endl;
        
        // 1. Notificar a la UI internamente
        State::EventBus::push_network_message("{\"event\": \"internal_conn\", \"status\": 2}");
        
        // 2. Mandar PING inmediato para figurar en el Panel de Gestión ("En línea")
        webSocket.send("{\"action\": \"ping\"}");
        
        // 3. Solicitar configuración base para asegurar que tenemos el ID de mesa correcto
        // (Esto forzará el evento 'config' del servidor)
        webSocket.send("{\"action\": \"sync_config\"}"); 
        
    } else if (msg->type == ix::WebSocketMessageType::Close) {
        std::cout << "⚠️ [SOCKET] Connection closed." << std::endl;
        State::EventBus::push_network_message("{\"event\": \"internal_conn\", \"status\": 0}");
    } else if (msg->type == ix::WebSocketMessageType::Error) {
        std::cout << "❌ [SOCKET] Connection error: " << msg->errorInfo.reason << std::endl;
        State::EventBus::push_network_message("{\"event\": \"internal_conn\", \"status\": 0}");
    }
}

void SocketController::start() {
    std::cout << "Starting Native IoT Session..." << std::endl;
    std::cout << "Connecting to: " << ws_url << std::endl;

    webSocket.start();
    is_running = true;
}

void SocketController::stop() {
    is_running = false;
    webSocket.stop();
}

void SocketController::update() {
    static uint32_t last_app_ping = SDL_GetTicks(); // Initialize with current time to avoid immediate double-ping
    uint32_t now = SDL_GetTicks();
    
    // Heartbeat cada 25 segundos (más conservador que 30)
    if (now - last_app_ping > 25000) {
        if (webSocket.getReadyState() == ix::ReadyState::Open) {
            webSocket.send("{\"action\": \"ping\"}");
            last_app_ping = now;
        }
    }

    // Procesar acciones de la UI hacia el servidor
    State::UIAction ui_act;
    while (State::EventBus::pop_ui_action(ui_act)) {
        if (webSocket.getReadyState() == ix::ReadyState::Open) {
            JsonDocument doc;
            doc["action"] = ui_act.type;
            
            if (!ui_act.payload.empty()) {
                doc["payload"] = ui_act.payload;
            }
            
            std::string output;
            serializeJson(doc, output);
            webSocket.send(output);
            
            std::cout << "📤 [UI -> NET] Sent Action: " << ui_act.type << std::endl;
        } else {
            std::cout << "⚠️ [NET] Action dropped: Socket not Open (State: " << (int)webSocket.getReadyState() << ")" << std::endl;
        }
    }
}

} // namespace Network
