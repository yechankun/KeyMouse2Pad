#pragma once

#include <cstdint>
#include <string>

namespace converter {

enum class GamepadButton : std::uint32_t {
    A = 1u << 0,
    B = 1u << 1,
    X = 1u << 2,
    Y = 1u << 3,
    LeftBumper = 1u << 4,
    RightBumper = 1u << 5,
    Back = 1u << 6,
    Start = 1u << 7,
    LeftThumb = 1u << 8,
    RightThumb = 1u << 9,
    DpadUp = 1u << 10,
    DpadDown = 1u << 11,
    DpadLeft = 1u << 12,
    DpadRight = 1u << 13,
};

struct GamepadState {
    std::int16_t left_x = 0;
    std::int16_t left_y = 0;
    std::int16_t right_x = 0;
    std::int16_t right_y = 0;
    std::uint8_t left_trigger = 0;
    std::uint8_t right_trigger = 0;
    std::uint32_t buttons = 0;

    [[nodiscard]] bool pressed(GamepadButton button) const;
    void set(GamepadButton button, bool is_pressed);
};

std::string describe(const GamepadState& state);

} // namespace converter

