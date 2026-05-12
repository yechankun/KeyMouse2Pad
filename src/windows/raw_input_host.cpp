#ifdef _WIN32

#include "converter/input_state.hpp"

#include <windows.h>

namespace converter::windows {

// TODO: Register keyboard and mouse with RegisterRawInputDevices, translate
// WM_INPUT packets into InputSnapshot updates, and keep UI work off this thread.
class RawInputHost {
public:
    bool start()
    {
        return false;
    }
};

} // namespace converter::windows

#endif

