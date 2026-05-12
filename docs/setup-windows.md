# Windows Setup

## Requirements

- Windows 10 or later.
- Python 3.12 or compatible Python 3 for source runs.
- ViGEm-compatible environment for Xbox 360 controller output through
  `vgamepad`.

Some games or elevated applications may require running KeyMouse2Pad as
administrator for input capture to work consistently.

## Run From Source

```bat
run_gui.bat
```

The GUI stores mappings at:

```text
%LOCALAPPDATA%\KeyMouse2Pad\profile.json
```

## Build Exe

```bat
build_exe.bat
```

The executable is written to:

```text
dist\KeyMouse2Pad.exe
```

## Controls

- `F8`: Toggle converter running state.
- `F9`: Toggle exclusive pad mode.

Exclusive pad mode converts mapped keyboard and mouse input to gamepad output
and blocks the original keyboard/mouse events from reaching the focused app.

## Troubleshooting

- If controller output is unavailable, check the GUI status text first.
- If input capture does not work in a game, try running KeyMouse2Pad as
  administrator.
- If mappings feel wrong, open the mapping section in the GUI and save a new
  profile.
