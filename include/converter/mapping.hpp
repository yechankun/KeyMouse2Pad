#pragma once

#include "converter/gamepad_state.hpp"
#include "converter/input_state.hpp"

#include <string>
#include <unordered_map>

namespace converter {

struct AxisKeys {
    std::string negative;
    std::string positive;
};

struct StickKeyMapping {
    AxisKeys x;
    AxisKeys y;
};

struct AnalogSettings {
    float deadzone = 0.05f;
    float left_ramp_up_per_second = 18.0f;
    float left_ramp_down_per_second = 24.0f;
    float mouse_sensitivity = 0.018f;
    float mouse_smoothing = 0.35f;
    float mouse_recenter_per_second = 7.5f;
};

struct MappingProfile {
    std::unordered_map<std::string, GamepadButton> key_buttons;
    std::unordered_map<MouseButton, GamepadButton> mouse_buttons;
    std::unordered_map<std::string, bool> left_trigger_keys;
    std::unordered_map<std::string, bool> right_trigger_keys;
    std::unordered_map<MouseButton, bool> left_trigger_mouse_buttons;
    std::unordered_map<MouseButton, bool> right_trigger_mouse_buttons;
    StickKeyMapping left_stick;
    AnalogSettings analog;
};

class MappingEngine {
public:
    explicit MappingEngine(MappingProfile profile);

    [[nodiscard]] GamepadState update(const InputSnapshot& input, float delta_seconds);
    void reset();

private:
    MappingProfile profile_;
    float left_x_ = 0.0f;
    float left_y_ = 0.0f;
    float right_x_ = 0.0f;
    float right_y_ = 0.0f;

    [[nodiscard]] float axis_from_keys(const InputSnapshot& input, const AxisKeys& keys) const;
    [[nodiscard]] float apply_deadzone(float value) const;
    [[nodiscard]] static std::int16_t to_stick_value(float value);
};

MappingProfile default_profile();

} // namespace converter
