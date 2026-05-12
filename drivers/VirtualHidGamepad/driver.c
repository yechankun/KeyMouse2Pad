#include <initguid.h>

#include "driver.h"

NTSTATUS
DriverEntry(
    _In_ PDRIVER_OBJECT DriverObject,
    _In_ PUNICODE_STRING RegistryPath
    )
{
    WDF_DRIVER_CONFIG config;

    WDF_DRIVER_CONFIG_INIT(&config, ConverterEvtDeviceAdd);
    return WdfDriverCreate(
        DriverObject,
        RegistryPath,
        WDF_NO_OBJECT_ATTRIBUTES,
        &config,
        WDF_NO_HANDLE);
}

NTSTATUS
ConverterEvtDeviceAdd(
    _In_ WDFDRIVER Driver,
    _Inout_ PWDFDEVICE_INIT DeviceInit
    )
{
    NTSTATUS status;
    WDFDEVICE device;
    WDF_OBJECT_ATTRIBUTES deviceAttributes;
    WDF_IO_QUEUE_CONFIG queueConfig;
    PDEVICE_CONTEXT context;
    VHF_CONFIG vhfConfig;

    UNREFERENCED_PARAMETER(Driver);
    PAGED_CODE();

    WdfDeviceInitSetDeviceType(DeviceInit, FILE_DEVICE_CONVERTER_GAMEPAD);
    WdfDeviceInitSetIoType(DeviceInit, WdfDeviceIoBuffered);

    WDF_OBJECT_ATTRIBUTES_INIT_CONTEXT_TYPE(&deviceAttributes, DEVICE_CONTEXT);
    deviceAttributes.EvtCleanupCallback = ConverterEvtDeviceContextCleanup;

    status = WdfDeviceCreate(&DeviceInit, &deviceAttributes, &device);
    if (!NT_SUCCESS(status)) {
        return status;
    }

    context = DeviceGetContext(device);
    RtlZeroMemory(context, sizeof(*context));
    context->CurrentReport.report_id = CONVERTER_GAMEPAD_REPORT_ID;

    status = WdfDeviceCreateDeviceInterface(
        device,
        &GUID_DEVINTERFACE_CONVERTER_GAMEPAD,
        NULL);
    if (!NT_SUCCESS(status)) {
        return status;
    }

    WDF_IO_QUEUE_CONFIG_INIT_DEFAULT_QUEUE(&queueConfig, WdfIoQueueDispatchSequential);
    queueConfig.EvtIoDeviceControl = ConverterEvtIoDeviceControl;

    status = WdfIoQueueCreate(device, &queueConfig, WDF_NO_OBJECT_ATTRIBUTES, WDF_NO_HANDLE);
    if (!NT_SUCCESS(status)) {
        return status;
    }

    VHF_CONFIG_INIT(
        &vhfConfig,
        WdfDeviceWdmGetDeviceObject(device),
        sizeof(kConverterGamepadHidReportDescriptor),
        (PUCHAR)kConverterGamepadHidReportDescriptor);

    vhfConfig.VendorID = 0x1209;
    vhfConfig.ProductID = 0xC0DE;
    vhfConfig.VersionNumber = 0x0001;

    status = VhfCreate(&vhfConfig, &context->VhfHandle);
    if (!NT_SUCCESS(status)) {
        context->VhfHandle = NULL;
        return status;
    }

    status = VhfStart(context->VhfHandle);
    if (!NT_SUCCESS(status)) {
        VhfDelete(context->VhfHandle, TRUE);
        context->VhfHandle = NULL;
        return status;
    }

    return STATUS_SUCCESS;
}

VOID
ConverterEvtDeviceContextCleanup(
    _In_ WDFOBJECT DeviceObject
    )
{
    PDEVICE_CONTEXT context = DeviceGetContext((WDFDEVICE)DeviceObject);

    if (context->VhfHandle != NULL) {
        VhfDelete(context->VhfHandle, TRUE);
        context->VhfHandle = NULL;
    }
}

VOID
ConverterEvtIoDeviceControl(
    _In_ WDFQUEUE Queue,
    _In_ WDFREQUEST Request,
    _In_ size_t OutputBufferLength,
    _In_ size_t InputBufferLength,
    _In_ ULONG IoControlCode
    )
{
    NTSTATUS status = STATUS_SUCCESS;
    WDFDEVICE device = WdfIoQueueGetDevice(Queue);
    PDEVICE_CONTEXT context = DeviceGetContext(device);
    ConverterGamepadReport* inputReport = NULL;
    HID_XFER_PACKET transferPacket;

    UNREFERENCED_PARAMETER(OutputBufferLength);

    if (IoControlCode != IOCTL_CONVERTER_SET_GAMEPAD_REPORT) {
        WdfRequestComplete(Request, STATUS_INVALID_DEVICE_REQUEST);
        return;
    }

    if (InputBufferLength < sizeof(ConverterGamepadReport)) {
        WdfRequestComplete(Request, STATUS_BUFFER_TOO_SMALL);
        return;
    }

    status = WdfRequestRetrieveInputBuffer(
        Request,
        sizeof(ConverterGamepadReport),
        (PVOID*)&inputReport,
        NULL);
    if (!NT_SUCCESS(status)) {
        WdfRequestComplete(Request, status);
        return;
    }

    context->CurrentReport = *inputReport;
    context->CurrentReport.report_id = CONVERTER_GAMEPAD_REPORT_ID;

    RtlZeroMemory(&transferPacket, sizeof(transferPacket));
    transferPacket.reportId = CONVERTER_GAMEPAD_REPORT_ID;
    transferPacket.reportBuffer = (PUCHAR)&context->CurrentReport;
    transferPacket.reportBufferLen = sizeof(context->CurrentReport);

    status = VhfReadReportSubmit(context->VhfHandle, &transferPacket);
    WdfRequestComplete(Request, status);
}
