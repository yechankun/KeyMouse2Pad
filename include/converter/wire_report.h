#pragma once

#include <stdint.h>

#define CONVERTER_GAMEPAD_REPORT_ID 1u

#if defined(_MSC_VER)
#define CONVERTER_PACKED_STRUCT(name) __pragma(pack(push, 1)) struct name __pragma(pack(pop))
#else
#define CONVERTER_PACKED_STRUCT(name) struct __attribute__((packed)) name
#endif

CONVERTER_PACKED_STRUCT(ConverterGamepadReport) {
    uint8_t report_id;
    uint16_t buttons;
    int16_t left_x;
    int16_t left_y;
    int16_t right_x;
    int16_t right_y;
    uint8_t left_trigger;
    uint8_t right_trigger;
};

#undef CONVERTER_PACKED_STRUCT

