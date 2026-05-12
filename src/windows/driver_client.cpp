#ifdef _WIN32

#include "converter/gamepad_state.hpp"
#include "converter/wire_report.hpp"

#include <windows.h>

namespace converter::windows {

// TODO: Open the KMDF device interface and submit ConverterGamepadReport through
// IOCTL_CONVERTER_SET_GAMEPAD_REPORT.
class DriverClient {
public:
    bool submit(const GamepadState&)
    {
        // TODO: Convert with to_wire_report and pass the packed bytes to DeviceIoControl.
        return false;
    }
};

} // namespace converter::windows

#endif
