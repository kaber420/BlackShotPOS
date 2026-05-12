#include "AppState.h"

namespace State {

std::mutex AppState::state_mutex;

ConnectionStatus AppState::current_status = ConnectionStatus::DISCONNECTED;
std::string AppState::business_name = "BLACKSHOT POS";
std::string AppState::table_id = "01";
bool AppState::offline_mode = false;
bool AppState::force_offline_fault = false;
uint32_t AppState::last_connected_time = 0;

ConnectionStatus AppState::get_connection_status() {
    std::lock_guard<std::mutex> lock(state_mutex);
    return current_status;
}

void AppState::set_connection_status(ConnectionStatus status) {
    std::lock_guard<std::mutex> lock(state_mutex);
    current_status = status;
}

std::string AppState::get_business_name() {
    std::lock_guard<std::mutex> lock(state_mutex);
    return business_name;
}

void AppState::set_business_name(const std::string& name) {
    std::lock_guard<std::mutex> lock(state_mutex);
    business_name = name;
}

std::string AppState::get_table_id() {
    std::lock_guard<std::mutex> lock(state_mutex);
    return table_id;
}

void AppState::set_table_id(const std::string& id) {
    std::lock_guard<std::mutex> lock(state_mutex);
    table_id = id;
}

bool AppState::is_offline_mode() {
    std::lock_guard<std::mutex> lock(state_mutex);
    return offline_mode;
}

void AppState::set_offline_mode(bool offline) {
    std::lock_guard<std::mutex> lock(state_mutex);
    offline_mode = offline;
}

bool AppState::is_force_offline_fault() {
    std::lock_guard<std::mutex> lock(state_mutex);
    return force_offline_fault;
}

void AppState::set_force_offline_fault(bool fault) {
    std::lock_guard<std::mutex> lock(state_mutex);
    force_offline_fault = fault;
}

uint32_t AppState::get_last_connected_time() {
    std::lock_guard<std::mutex> lock(state_mutex);
    return last_connected_time;
}

void AppState::set_last_connected_time(uint32_t time) {
    std::lock_guard<std::mutex> lock(state_mutex);
    last_connected_time = time;
}

} // namespace State
