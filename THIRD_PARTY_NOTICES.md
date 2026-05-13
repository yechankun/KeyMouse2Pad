# Third Party Notices

KeyMouse2Pad vendors the runtime files needed to package Windows releases
without relying on slow or fragile release-time dependency installation.

## vgamepad

- Project: `vgamepad`
- Version: `0.1.0`
- License: MIT
- Source: https://github.com/yannbouteiller/vgamepad
- Vendored path: `vendor/vgamepad`
- License file: `vendor/vgamepad/LICENSE`

The vendored copy includes only the Python runtime files used by the Windows
executable build.

## ViGEmClient

- Project: `ViGEmClient`
- License: MIT
- Source: https://github.com/nefarius/ViGEmClient
- Vendored files:
  - `vendor/vgamepad/win/vigem/client/x64/ViGEmClient.dll`
  - `vendor/vgamepad/win/vigem/client/x86/ViGEmClient.dll`
- License file: `vendor/vgamepad/win/vigem/client/LICENSE`

`ViGEmClient.dll` is the native client library used by `vgamepad` to communicate
with the ViGEmBus driver. ViGEmBus installer MSI files are not vendored.
