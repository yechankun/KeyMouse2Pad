#pragma once

#include <ntddk.h>
#include <wdf.h>
#include <vhf.h>

#include "hid_report_descriptor.h"
#include "public.h"

DRIVER_INITIALIZE DriverEntry;
EVT_WDF_DRIVER_DEVICE_ADD ConverterEvtDeviceAdd;
EVT_WDF_OBJECT_CONTEXT_CLEANUP ConverterEvtDeviceContextCleanup;
EVT_WDF_IO_QUEUE_IO_DEVICE_CONTROL ConverterEvtIoDeviceControl;

typedef struct _DEVICE_CONTEXT {
    VHFHANDLE VhfHandle;
    ConverterGamepadReport CurrentReport;
} DEVICE_CONTEXT, *PDEVICE_CONTEXT;

WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(DEVICE_CONTEXT, DeviceGetContext)

