param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8020,
    [string]$Device = "cpu",
    [string]$ComputeType = "default"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$CoreDir = Join-Path $RootDir "CoreSTT"

function Test-CompatiblePython {
    try {
        py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-CompatiblePython)) {
    Write-Host "Python 3.11 or newer is required."
    $answer = Read-Host "Install Python 3.11 with winget now? [y/N]"
    if ($answer -eq "y" -or $answer -eq "Y") {
        winget install --id Python.Python.3.11 -e
    } else {
        Write-Error "Install Python 3.11 or newer, then rerun this script."
    }
}

Set-Location $CoreDir
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}
& .venv\Scripts\python.exe -m pip install -r requirements.txt
& .venv\Scripts\python.exe server.py --host $HostAddress --port $Port --device $Device --compute-type $ComputeType
