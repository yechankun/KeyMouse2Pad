# KeyMouse2Pad VirtualHidGamepad Driver Boundary

This directory contains the Windows VHF/KMDF driver project for exposing the
converter as a HID gamepad device.

## Expected Driver Behavior

- Expose one HID gamepad collection through Virtual HID Framework.
- Accept reports from the user-mode converter service.
- Publish the latest report to HID clients.
- Handle device start, stop, power transition, and service disconnect.

## User-Mode To Driver Contract

The service should send a packed report matching
`include/converter/wire_report.h`:

```c
typedef struct ConverterGamepadReport {
    uint8_t report_id;
    uint16_t buttons;
    int16_t left_x;
    int16_t left_y;
    int16_t right_x;
    int16_t right_y;
    uint8_t left_trigger;
    uint8_t right_trigger;
} ConverterGamepadReport;
```

Recommended transport:

- MVP: `IOCTL_CONVERTER_SET_GAMEPAD_REPORT`
- High-frequency optimization: shared memory ring buffer plus notification event

## Build

Install Visual Studio with Windows Driver Kit, open an x64 Native Tools Command
Prompt, then run:

```bat
build_driver.bat
```

The project links `VhfKm.lib` and uses the VHF flow documented by Microsoft:
`VHF_CONFIG_INIT`, `VhfCreate`, `VhfStart`, and `VhfReadReportSubmit`.

## Test Install

Development installs require test signing or a signed catalog.

```powershell
.\install_test_driver.ps1 -EnableTestSigning
```

Reboot, build the driver, then install the root-enumerated test device with WDK
`devcon`:

```bat
devcon install ConverterVhf.inf Root\KeyMouse2Pad
```

## Notes

- Keep all mapping logic in user mode.
- The kernel driver only validates, stores, and publishes HID reports.
- The resulting device is a kernel-level HID gamepad, not a physical USB device.
