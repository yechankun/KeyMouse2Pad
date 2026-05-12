#include "converter/mapping.hpp"
#include "converter/wire_report.hpp"

#include <cassert>
#include <cstdlib>
#include <iostream>

namespace {

void require(bool condition, const char* message)
{
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}

void button_mapping_works()
{
    converter::MappingEngine engine(converter::default_profile());
    converter::InputSnapshot input;
    input.keys.insert("Space");

    const auto state = engine.update(input, 1.0f / 60.0f);
    require(state.pressed(converter::GamepadButton::A), "Space should map to A");
}

void diagonal_left_stick_is_normalized()
{
    converter::MappingEngine engine(converter::default_profile());
    converter::InputSnapshot input;
    input.keys.insert("W");
    input.keys.insert("D");

    converter::GamepadState state;
    for (int i = 0; i < 16; ++i) {
        state = engine.update(input, 1.0f / 60.0f);
    }

    require(state.left_x > 20000, "D should move left stick X positive");
    require(state.left_y > 20000, "W should move left stick Y positive");
    require(state.left_x < 26000, "diagonal X should not saturate");
    require(state.left_y < 26000, "diagonal Y should not saturate");
}

void left_stick_recenters()
{
    converter::MappingEngine engine(converter::default_profile());
    converter::InputSnapshot input;
    input.keys.insert("W");

    (void)engine.update(input, 1.0f / 60.0f);
    input.keys.clear();

    converter::GamepadState state;
    for (int i = 0; i < 8; ++i) {
        state = engine.update(input, 1.0f / 60.0f);
    }

    require(state.left_y == 0, "left stick should ramp down to center");
}

void mouse_delta_drives_right_stick_and_recenters()
{
    converter::MappingEngine engine(converter::default_profile());
    converter::InputSnapshot input;
    input.mouse_delta = {.x = 80, .y = -40};

    auto state = engine.update(input, 1.0f / 60.0f);
    require(state.right_x > 0, "mouse X should move right stick X");
    require(state.right_y > 0, "negative mouse Y should move right stick Y positive");

    input.mouse_delta = {};
    for (int i = 0; i < 16; ++i) {
        state = engine.update(input, 1.0f / 60.0f);
    }

    require(state.right_x == 0, "right stick X should recenter");
    require(state.right_y == 0, "right stick Y should recenter");
}

void mouse_buttons_drive_triggers()
{
    converter::MappingEngine engine(converter::default_profile());
    converter::InputSnapshot input;
    input.mouse_buttons.insert(converter::MouseButton::Left);
    input.mouse_buttons.insert(converter::MouseButton::Right);

    const auto state = engine.update(input, 1.0f / 60.0f);
    require(state.left_trigger == 255, "right mouse should map to left trigger");
    require(state.right_trigger == 255, "left mouse should map to right trigger");
}

void wire_report_matches_hid_descriptor_layout()
{
    converter::GamepadState state;
    state.set(converter::GamepadButton::A, true);
    state.left_x = 123;
    state.right_trigger = 255;

    const auto report = converter::to_wire_report(state);
    require(sizeof(report) == 13, "wire report should be packed to 13 bytes");
    require(report.report_id == CONVERTER_GAMEPAD_REPORT_ID, "wire report ID should be 1");
    require((report.buttons & 0x1u) != 0, "wire report should carry button bits");
    require(report.left_x == 123, "wire report should carry axes");
    require(report.right_trigger == 255, "wire report should carry triggers");
}

} // namespace

int main()
{
    button_mapping_works();
    diagonal_left_stick_is_normalized();
    left_stick_recenters();
    mouse_delta_drives_right_stick_and_recenters();
    mouse_buttons_drive_triggers();
    wire_report_matches_hid_descriptor_layout();

    std::cout << "mapping_tests: all tests passed\n";
    return 0;
}
