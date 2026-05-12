# KeyMouse2Pad

SPDX-License-Identifier: GPL-3.0-or-later

Keyboard and mouse to gamepad converter for Windows. The repository is
structured so the mapping engine can be tested without Windows Driver Kit,
while the Windows service and driver boundary are kept explicit.

## Current Scope

- Platform-independent mapping engine in C++20.
- Simple Tk GUI for testing the converter behavior interactively.
- System-wide Windows keyboard/mouse capture through low-level hooks.
- Windows Xbox 360 controller output through a kernel driver backend when available.
- Keyboard button mapping.
- WASD-to-left-stick analog synthesis.
- Mouse-delta-to-right-stick analog synthesis.
- Ramp, smoothing, deadzone, sensitivity, and recenter behavior.
- HID report layout notes for a future Windows kernel driver.
- Local tests that run on Linux/WSL with `g++`.

This is not yet a signed Windows kernel driver. A real Windows driver requires
WDK, test signing during development, and production signing before normal
distribution.

## Build And Test

```sh
make test
make demo
make gui
```

Run the demo:

```sh
./build/converter_demo
```

Run the GUI:

```sh
make run-gui
```

Windows:

```bat
run_gui.bat
```

Linux/WSL with desktop display:

```sh
./run_gui.sh
```

Build the Windows executable:

```bat
build_exe.bat
```

or from WSL:

```sh
make exe
```

The output is `dist/KeyMouse2Pad.exe`.

The GUI captures keyboard and mouse input globally on Windows when `Global capture`
is enabled. On Windows, it can submit the generated state to an Xbox 360
controller backend. Run as administrator if you need to capture input from
elevated applications.

## License

This project is licensed under the GNU General Public License v3.0 or later.
See `LICENSE` for the full license text.

## Target Runtime Architecture

```text
Keyboard / Mouse
        |
Windows Raw Input Service
        |
Mapping Engine
        |
Driver Client: IOCTL or shared memory
        |
Kernel HID Gamepad Driver
        |
Windows / Game
```

## Next Driver Milestone

1. Build `drivers/VirtualHidGamepad/VirtualHidGamepad.vcxproj` with Visual Studio + WDK.
2. Install the root-enumerated test device with WDK `devcon`.
3. Connect the GUI/service to `IOCTL_CONVERTER_SET_GAMEPAD_REPORT`.
4. Validate with `joy.cpl`, Gamepad Tester, Steam Input, and target games.
