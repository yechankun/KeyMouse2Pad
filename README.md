# KeyMouse2Pad

SPDX-License-Identifier: GPL-3.0-or-later

English | [한국어](README.ko.md)

KeyMouse2Pad converts keyboard and mouse input into gamepad controls on Windows.
It is built for players who want a lightweight keyboard/mouse-to-controller
converter with editable mappings and a simple GUI.

## Status

- Windows-focused GUI application.
- System-wide keyboard and mouse capture on Windows.
- Xbox 360 controller output through the `vgamepad` / ViGEm stack when available.
- Editable keyboard and mouse mappings saved locally.
- C++ mapping engine tests for the portable core.
- Experimental Windows HID driver boundary for future kernel-driver work.

This project is not a signed production kernel driver. Some runtime features may
need administrator privileges depending on the target game or application.

## Download

Stable builds are published from GitHub Releases once a version tag is created.
For development builds, run from source or build the executable locally.

## Run From Source

Windows:

```bat
run_gui.bat
```

Linux/WSL can run the mapping tests, but the actual input capture and controller
output features are Windows-only.

## Build

Build the Windows executable:

```bat
build_exe.bat
```

The output is:

```text
dist\KeyMouse2Pad.exe
```

Run local checks:

```sh
make test
make gui
```

On Windows without `make`, run the GUI smoke test directly:

```powershell
py -3 gui\converter_gui.py --self-test
```

## Documentation

- [Windows setup](docs/setup-windows.md)
- [Architecture](docs/architecture.md)
- [Branching](docs/branching.md)
- [Korean Windows setup](docs/setup-windows.ko.md)

## Contributing

Keep contributions small and practical. Open an issue for behavior changes, send
a PR for focused fixes, and let CI handle the repetitive checks.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

KeyMouse2Pad is licensed under the GNU General Public License v3.0 or later.
See [LICENSE](LICENSE).

Third-party runtime notices are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
