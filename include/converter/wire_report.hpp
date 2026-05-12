#pragma once

#include "converter/gamepad_state.hpp"
#include "converter/wire_report.h"

namespace converter {

inline ConverterGamepadReport to_wire_report(const GamepadState& state)
{
    return ConverterGamepadReport {
        .report_id = CONVERTER_GAMEPAD_REPORT_ID,
        .buttons = static_cast<std::uint16_t>(state.buttons & 0xFFFFu),
        .left_x = state.left_x,
        .left_y = state.left_y,
        .right_x = state.right_x,
        .right_y = state.right_y,
        .left_trigger = state.left_trigger,
        .right_trigger = state.right_trigger,
    };
}

} // namespace converter

