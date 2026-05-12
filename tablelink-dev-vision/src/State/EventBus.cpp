#include "EventBus.h"

namespace State {

std::queue<std::string> EventBus::message_queue;
std::mutex EventBus::message_mutex;

std::vector<UIAction> EventBus::action_queue;
std::mutex EventBus::action_mutex;

void EventBus::push_network_message(const std::string& msg) {
    std::lock_guard<std::mutex> lock(message_mutex);
    message_queue.push(msg);
}

bool EventBus::pop_network_message(std::string& msg) {
    std::lock_guard<std::mutex> lock(message_mutex);
    if (message_queue.empty()) return false;
    msg = message_queue.front();
    message_queue.pop();
    return true;
}

void EventBus::push_ui_action(const UIAction& action) {
    std::lock_guard<std::mutex> lock(action_mutex);
    action_queue.push_back(action);
}

bool EventBus::pop_ui_action(UIAction& action) {
    std::lock_guard<std::mutex> lock(action_mutex);
    if (action_queue.empty()) return false;
    action = action_queue.front();
    action_queue.erase(action_queue.begin());
    return true;
}

} // namespace State
