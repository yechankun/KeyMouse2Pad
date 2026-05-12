# Windows Integration Skeleton

The files in this directory are placeholders for the Windows-specific runtime:

- `raw_input_host.cpp`: should own the hidden message window and Raw Input
  registration for keyboard and mouse devices.
- `driver_client.cpp`: should open the converter device interface and submit
  packed gamepad reports through IOCTL.

These files are not part of the portable Linux/WSL test build.

