# Architecture

KeyMouse2Pad keeps the high-frequency input work simple and local.

```text
Keyboard / Mouse
        |
Windows hooks + Raw Input
        |
Mapping profile
        |
Mapping engine
        |
Controller backend
        |
Windows / Game
```

## Components

- `gui/converter_gui.py`: Windows GUI, global input capture, mapping editor, and
  runtime controller output.
- `src/converter` and `include/converter`: portable C++ mapping engine prototype.
- `tests`: mapping-engine tests.
- `drivers/VirtualHidGamepad`: experimental Windows VHF/KMDF driver boundary.
- `config/default_profile.json`: reference mapping profile.

## Runtime Model

The GUI keeps the current keyboard/mouse state, applies the selected mapping,
and submits a gamepad-shaped state to the controller backend. In exclusive mode,
mapped keyboard and mouse events are blocked from the focused application after
the converter records them.

## Driver Direction

The driver directory documents the future kernel HID gamepad boundary. Mapping
logic should stay in user mode. The driver should only validate, store, and
publish HID reports.
