#ifndef BS_APP_STATE_H
#define BS_APP_STATE_H

#include <string>
#include <mutex>
#include <cstdint>

namespace State {

enum class ConnectionStatus {
    DISCONNECTED = 0,
    CONNECTING = 1,
    CONNECTED = 2
};

class AppState {
public:
    static ConnectionStatus get_connection_status();
    static void set_connection_status(ConnectionStatus status);

    static std::string get_business_name();
    static void set_business_name(const std::string& name);

    static std::string get_table_id();
    static void set_table_id(const std::string& id);

    static bool is_offline_mode();
    static void set_offline_mode(bool offline);

    static bool is_force_offline_fault();
    static void set_force_offline_fault(bool fault);

    static uint32_t get_last_connected_time();
    static void set_last_connected_time(uint32_t time);

private:
    static std::mutex state_mutex;

    static ConnectionStatus current_status;
    static std::string business_name;
    static std::string table_id;
    static bool offline_mode;
    static bool force_offline_fault;
    static uint32_t last_connected_time;
};

} // namespace State

#endif // BS_APP_STATE_H
