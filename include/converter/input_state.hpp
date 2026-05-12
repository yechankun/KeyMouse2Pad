#pragma once

#include <string>
#include <unordered_set>

namespace converter {

enum class MouseButton {
    Left,
    Right,
    Middle,
    X1,
    X2,
};

struct MouseDelta {
    int x = 0;
    int y = 0;
};

struct InputSnapshot {
    std::unordered_set<std::string> keys;
    std::unordered_set<MouseButton> mouse_buttons;
    MouseDelta mouse_delta;

    [[nodiscard]] bool key_down(const std::string& key) const;
    [[nodiscard]] bool mouse_down(MouseButton button) const;
};

} // namespace converter

