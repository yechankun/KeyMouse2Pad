#include "converter/mapping.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <utility>

namespace converter {

namespace {

constexpr float kSqrtHalf = 0.70710678118f;

float clamp_unit(float value)
{
    return std::clamp(value, -1.0f, 1.0f);
}

float move_towards(float current, float target, float max_delta)
{
    if (current < target) {
        return std::min(current + max_delta, target);
    }
    return std::max(current - max_delta, target);
}

std::string button_name(GamepadButton button)
{
    switch (button) {
    case GamepadButton::A:
        return "A";
    case GamepadButton::B:
        return "B";
    case GamepadButton::X:
        return "X";
    case GamepadButton::Y:
        return "Y";
    case GamepadButton::LeftBumper:
        return "LB";
    case GamepadButton::RightBumper:
        return "RB";
    case GamepadButton::Back:
        return "Back";
    case GamepadButton::Start:
        return "Start";
    case GamepadButton::LeftThumb:
        return "LS";
    case GamepadButton::RightThumb:
        return "RS";
    case GamepadButton::DpadUp:
        return "DUp";
    case GamepadButton::DpadDown:
        return "DDown";
    case GamepadButton::DpadLeft:
        return "DLeft";
    case GamepadButton::DpadRight:
        return "DRight";
    }
    return "?";
}

} // namespace

bool GamepadState::pressed(GamepadButton button) const
{
    return (buttons & static_cast<std::uint32_t>(button)) != 0;
}

void GamepadState::set(GamepadButton button, bool is_pressed)
{
    const auto bit = static_cast<std::uint32_t>(button);
    if (is_pressed) {
        buttons |= bit;
    } else {
        buttons &= ~bit;
    }
}

std::string describe(const GamepadState& state)
{
    std::ostringstream out;
    out << "LX=" << state.left_x << " LY=" << state.left_y << " RX=" << state.right_x
        << " RY=" << state.right_y << " LT=" << static_cast<int>(state.left_trigger)
        << " RT=" << static_cast<int>(state.right_trigger) << " Buttons=[";

    bool first = true;
    const GamepadButton all_buttons[] = {
        GamepadButton::A,        GamepadButton::B,          GamepadButton::X,
        GamepadButton::Y,        GamepadButton::LeftBumper, GamepadButton::RightBumper,
        GamepadButton::Back,     GamepadButton::Start,      GamepadButton::LeftThumb,
        GamepadButton::RightThumb, GamepadButton::DpadUp,   GamepadButton::DpadDown,
        GamepadButton::DpadLeft, GamepadButton::DpadRight,
    };

    for (const auto button : all_buttons) {
        if (!state.pressed(button)) {
            continue;
        }
        if (!first) {
            out << ",";
        }
        out << button_name(button);
        first = false;
    }
    out << "]";
    return out.str();
}

bool InputSnapshot::key_down(const std::string& key) const
{
    return keys.find(key) != keys.end();
}

bool InputSnapshot::mouse_down(MouseButton button) const
{
    return mouse_buttons.find(button) != mouse_buttons.end();
}

MappingEngine::MappingEngine(MappingProfile profile)
    : profile_(std::move(profile))
{
}

GamepadState MappingEngine::update(const InputSnapshot& input, float delta_seconds)
{
    delta_seconds = std::max(delta_seconds, 0.0f);

    GamepadState state;
    for (const auto& [key, button] : profile_.key_buttons) {
        state.set(button, input.key_down(key));
    }
    for (const auto& [button, gamepad_button] : profile_.mouse_buttons) {
        state.set(gamepad_button, input.mouse_down(button));
    }
    for (const auto& [key, _] : profile_.left_trigger_keys) {
        if (input.key_down(key)) {
            state.left_trigger = 255;
            break;
        }
    }
    for (const auto& [key, _] : profile_.right_trigger_keys) {
        if (input.key_down(key)) {
            state.right_trigger = 255;
            break;
        }
    }
    for (const auto& [button, _] : profile_.left_trigger_mouse_buttons) {
        if (input.mouse_down(button)) {
            state.left_trigger = 255;
            break;
        }
    }
    for (const auto& [button, _] : profile_.right_trigger_mouse_buttons) {
        if (input.mouse_down(button)) {
            state.right_trigger = 255;
            break;
        }
    }

    float target_left_x = axis_from_keys(input, profile_.left_stick.x);
    float target_left_y = axis_from_keys(input, profile_.left_stick.y);
    if (target_left_x != 0.0f && target_left_y != 0.0f) {
        target_left_x *= kSqrtHalf;
        target_left_y *= kSqrtHalf;
    }

    const auto ramp_x = (std::abs(target_left_x) > std::abs(left_x_))
        ? profile_.analog.left_ramp_up_per_second
        : profile_.analog.left_ramp_down_per_second;
    const auto ramp_y = (std::abs(target_left_y) > std::abs(left_y_))
        ? profile_.analog.left_ramp_up_per_second
        : profile_.analog.left_ramp_down_per_second;
    left_x_ = move_towards(left_x_, target_left_x, ramp_x * delta_seconds);
    left_y_ = move_towards(left_y_, target_left_y, ramp_y * delta_seconds);

    const float mouse_target_x =
        clamp_unit(static_cast<float>(input.mouse_delta.x) * profile_.analog.mouse_sensitivity);
    const float mouse_target_y =
        clamp_unit(static_cast<float>(-input.mouse_delta.y) * profile_.analog.mouse_sensitivity);
    const float smoothing = std::clamp(profile_.analog.mouse_smoothing, 0.0f, 1.0f);

    if (input.mouse_delta.x != 0 || input.mouse_delta.y != 0) {
        right_x_ = clamp_unit(right_x_ * smoothing + mouse_target_x * (1.0f - smoothing));
        right_y_ = clamp_unit(right_y_ * smoothing + mouse_target_y * (1.0f - smoothing));
    } else {
        const float recenter = profile_.analog.mouse_recenter_per_second * delta_seconds;
        right_x_ = move_towards(right_x_, 0.0f, recenter);
        right_y_ = move_towards(right_y_, 0.0f, recenter);
    }

    state.left_x = to_stick_value(apply_deadzone(left_x_));
    state.left_y = to_stick_value(apply_deadzone(left_y_));
    state.right_x = to_stick_value(apply_deadzone(right_x_));
    state.right_y = to_stick_value(apply_deadzone(right_y_));

    return state;
}

void MappingEngine::reset()
{
    left_x_ = 0.0f;
    left_y_ = 0.0f;
    right_x_ = 0.0f;
    right_y_ = 0.0f;
}

float MappingEngine::axis_from_keys(const InputSnapshot& input, const AxisKeys& keys) const
{
    float value = 0.0f;
    if (!keys.negative.empty() && input.key_down(keys.negative)) {
        value -= 1.0f;
    }
    if (!keys.positive.empty() && input.key_down(keys.positive)) {
        value += 1.0f;
    }
    return value;
}

float MappingEngine::apply_deadzone(float value) const
{
    const float deadzone = std::clamp(profile_.analog.deadzone, 0.0f, 0.95f);
    if (std::abs(value) < deadzone) {
        return 0.0f;
    }
    const float sign = value < 0.0f ? -1.0f : 1.0f;
    return sign * ((std::abs(value) - deadzone) / (1.0f - deadzone));
}

std::int16_t MappingEngine::to_stick_value(float value)
{
    value = clamp_unit(value);
    if (value >= 0.0f) {
        return static_cast<std::int16_t>(std::round(value * 32767.0f));
    }
    return static_cast<std::int16_t>(std::round(value * 32768.0f));
}

MappingProfile default_profile()
{
    MappingProfile profile;
    profile.left_stick = {
        .x = {.negative = "A", .positive = "D"},
        .y = {.negative = "S", .positive = "W"},
    };

    profile.key_buttons = {
        {"Space", GamepadButton::A},
        {"LeftCtrl", GamepadButton::B},
        {"E", GamepadButton::X},
        {"R", GamepadButton::Y},
        {"Q", GamepadButton::LeftBumper},
        {"F", GamepadButton::RightBumper},
        {"Tab", GamepadButton::Back},
        {"Enter", GamepadButton::Start},
        {"Up", GamepadButton::DpadUp},
        {"Down", GamepadButton::DpadDown},
        {"Left", GamepadButton::DpadLeft},
        {"Right", GamepadButton::DpadRight},
    };

    profile.mouse_buttons = {
        {MouseButton::Middle, GamepadButton::RightThumb},
        {MouseButton::X1, GamepadButton::LeftBumper},
        {MouseButton::X2, GamepadButton::RightBumper},
    };

    profile.left_trigger_keys = {{"LeftShift", true}};
    profile.right_trigger_keys = {};
    profile.left_trigger_mouse_buttons = {{MouseButton::Right, true}};
    profile.right_trigger_mouse_buttons = {{MouseButton::Left, true}};

    return profile;
}

} // namespace converter
