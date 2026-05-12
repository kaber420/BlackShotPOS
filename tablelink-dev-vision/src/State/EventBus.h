#ifndef BS_EVENT_BUS_H
#define BS_EVENT_BUS_H

#include <string>
#include <queue>
#include <mutex>
#include <vector>

namespace State {

struct UIAction {
    std::string type;
    std::string payload;
};

class EventBus {
public:
    // Network to UI
    static void push_network_message(const std::string& msg);
    static bool pop_network_message(std::string& msg);

    // UI to Network
    static void push_ui_action(const UIAction& action);
    static bool pop_ui_action(UIAction& action);

private:
    static std::queue<std::string> message_queue;
    static std::mutex message_mutex;

    static std::vector<UIAction> action_queue;
    static std::mutex action_mutex;
};

} // namespace State

#endif // BS_EVENT_BUS_H
