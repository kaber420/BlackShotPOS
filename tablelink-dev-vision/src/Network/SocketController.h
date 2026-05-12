#ifndef BS_SOCKET_CONTROLLER_H
#define BS_SOCKET_CONTROLLER_H

#include <string>
#include <thread>
#include <atomic>
#include <ixwebsocket/IXWebSocket.h>

namespace Network {

class SocketController {
public:
    static SocketController& get_instance() {
        static SocketController instance;
        return instance;
    }

    void init(const std::string& host, const std::string& token);
    void start();
    void stop();
    
    // Llamar en el bucle secundario para procesar outgoing messages
    void update();

private:
    SocketController() : is_running(false) {}
    ~SocketController() { stop(); }

    SocketController(const SocketController&) = delete;
    SocketController& operator=(const SocketController&) = delete;

    ix::WebSocket webSocket;
    std::string ws_url;
    std::thread network_thread;
    std::atomic<bool> is_running;

    void on_message(const ix::WebSocketMessagePtr& msg);
};

} // namespace Network

#endif // BS_SOCKET_CONTROLLER_H
