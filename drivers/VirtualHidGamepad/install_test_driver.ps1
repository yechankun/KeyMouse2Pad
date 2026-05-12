param(
    [switch]$EnableTestSigning
)

$ErrorActionPreference = "Stop"
$driverDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$infPath = Join-Path $driverDir "ConverterVhf.inf"

if ($EnableTestSigning) {
    bcdedit /set testsigning on
    Write-Host "Test signing enabled. Reboot Windows before installing the driver."
    exit 0
}

if (-not (Test-Path $infPath)) {
    throw "INF not found: $infPath"
}

pnputil /add-driver $infPath /install

Write-Host "Driver staged. For a root-enumerated test device, use devcon from WDK:"
Write-Host "devcon install `"$infPath`" Root\KeyMouse2Pad"
