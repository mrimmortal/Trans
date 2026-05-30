param(
    [Parameter(Position = 0)]
    [ValidateSet("win-dev", "uat-win", "prod-win", "help")]
    [string]$Command = "help",

    [string]$SourceDir = "",
    [string]$InstallRoot = "C:\Apps\medical-dictation",
    [string]$BackendEnvContent = "",
    [string]$FrontendEnvContent = "",
    [string]$BackendServiceName = "",
    [string]$FrontendServiceName = ""
)

$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Show-Help {
    Write-Host @"
Usage:
  .\scripts\run.ps1 win-dev
  .\scripts\run.ps1 uat-win  -SourceDir C:\path\to\medical-dictation
  .\scripts\run.ps1 prod-win -SourceDir C:\path\to\medical-dictation

Optional deploy parameters:
  -InstallRoot C:\Apps\medical-dictation
  -BackendEnvContent  <env file content from GitHub secret>
  -FrontendEnvContent <env file content from GitHub secret>
  -BackendServiceName TranscriptionTemplateBackendUAT
  -FrontendServiceName TranscriptionTemplateFrontendUAT
"@
}

function Import-EnvFile {
    param(
        [string]$Path,
        [string]$FallbackPath = ""
    )

    if (-not (Test-Path $Path)) {
        if (-not [string]::IsNullOrWhiteSpace($FallbackPath) -and (Test-Path $FallbackPath)) {
            Write-Warning "$Path was not found; using $FallbackPath"
            $Path = $FallbackPath
        }
        else {
            throw "Environment file not found: $Path"
        }
    }

    Get-Content $Path | ForEach-Object {
        $Line = $_.Trim()
        if ($Line.Length -eq 0 -or $Line.StartsWith("#")) {
            return
        }

        $Parts = $Line.Split("=", 2)
        if ($Parts.Length -eq 2) {
            [Environment]::SetEnvironmentVariable($Parts[0].Trim(), $Parts[1].Trim(), "Process")
        }
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Script
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $Script
}

function Get-PythonCommand {
    foreach ($PythonCommand in @("py -3", "python", "python3")) {
        try {
            $Parts = $PythonCommand.Split(" ")
            $Exe = $Parts[0]
            $Args = @()
            if ($Parts.Length -gt 1) {
                $Args = $Parts[1..($Parts.Length - 1)]
            }
            & $Exe @Args --version | Out-Null
            return $PythonCommand
        }
        catch {
            continue
        }
    }

    throw "Python 3 was not found. Install Python 3.11+ on this host."
}

function Invoke-Python {
    param(
        [string]$PythonCommand,
        [string[]]$Arguments
    )

    $Parts = $PythonCommand.Split(" ")
    $Exe = $Parts[0]
    $PrefixArgs = @()
    if ($Parts.Length -gt 1) {
        $PrefixArgs = $Parts[1..($Parts.Length - 1)]
    }

    & $Exe @PrefixArgs @Arguments
}

function Invoke-NodeScript {
    param([string]$ScriptName)

    if (Get-Command pnpm -ErrorAction SilentlyContinue) {
        if ($ScriptName -eq "install") {
            pnpm install --frozen-lockfile
        }
        else {
            pnpm $ScriptName
        }
    }
    else {
        if ($ScriptName -eq "install") {
            npm install
        }
        else {
            npm run $ScriptName
        }
    }
}

function Ensure-BackendVenv {
    param([string]$RequirementsPath)

    $PythonCommand = Get-PythonCommand
    $VenvDir = Join-Path $BackendDir "venv"
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"

    if (-not (Test-Path $VenvPython)) {
        Invoke-Python $PythonCommand @("-m", "venv", $VenvDir)
    }

    $RequirementsHash = (Get-FileHash -Path $RequirementsPath -Algorithm SHA256).Hash
    $MarkerPath = Join-Path $VenvDir ".$((Split-Path $RequirementsPath -Leaf)).sha256"
    $ExistingHash = ""
    if (Test-Path $MarkerPath) {
        $ExistingHash = (Get-Content $MarkerPath -Raw).Trim()
    }

    if ($ExistingHash -ne $RequirementsHash) {
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r $RequirementsPath
        Set-Content -Path $MarkerPath -Value $RequirementsHash -NoNewline
    }
}

function Start-WinDev {
    Import-EnvFile (Join-Path $BackendDir ".env.windows") (Join-Path $BackendDir ".env.example")

    Ensure-BackendVenv (Join-Path $BackendDir "requirements.txt")
    $PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"

    $Backend = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList "run.py" `
        -WorkingDirectory $BackendDir `
        -PassThru

    try {
        Start-Sleep -Seconds 3
        Import-EnvFile (Join-Path $FrontendDir ".env.local.windows")
        if ([string]::IsNullOrWhiteSpace($env:FRONTEND_PORT)) {
            $env:PORT = "3000"
        }
        else {
            $env:PORT = $env:FRONTEND_PORT
        }
        Set-Location $FrontendDir
        Invoke-NodeScript dev
    }
    finally {
        if ($Backend -and -not $Backend.HasExited) {
            Stop-Process -Id $Backend.Id -Force
        }
    }
}

function Restart-AppServices {
    param(
        [string]$BackendName,
        [string]$FrontendName
    )

    foreach ($ServiceName in @($BackendName, $FrontendName)) {
        if ([string]::IsNullOrWhiteSpace($ServiceName)) {
            continue
        }

        $Service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($null -eq $Service) {
            Write-Warning "Service '$ServiceName' was not found. Skipping restart."
            continue
        }

        Restart-Service -Name $ServiceName -Force
        Get-Service -Name $ServiceName
    }
}

function Deploy-Win {
    param(
        [ValidateSet("uat-win", "prod-win")]
        [string]$EnvironmentName
    )

    if ([string]::IsNullOrWhiteSpace($SourceDir)) {
        throw "-SourceDir is required for $EnvironmentName deployments."
    }

    $ResolvedSource = (Resolve-Path $SourceDir).Path
    $EnvironmentRoot = Join-Path $InstallRoot $EnvironmentName
    $ReleaseStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $ReleaseRoot = Join-Path $EnvironmentRoot "releases\$ReleaseStamp"
    $CurrentRoot = Join-Path $EnvironmentRoot "current"

    Invoke-Step "Prepare release folders" {
        New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null
        New-Item -ItemType Directory -Force -Path (Join-Path $EnvironmentRoot "shared") | Out-Null
    }

    Invoke-Step "Copy artifact" {
        Copy-Item -Path (Join-Path $ResolvedSource "*") -Destination $ReleaseRoot -Recurse -Force
    }

    Invoke-Step "Write environment files" {
        $BackendEnvPath = Join-Path $ReleaseRoot "backend\.env"
        $FrontendEnvPath = Join-Path $ReleaseRoot "frontend\.env.production"

        if ($BackendEnvContent.Trim().Length -gt 0) {
            Set-Content -Path $BackendEnvPath -Value $BackendEnvContent -Encoding UTF8
        }
        elseif ($EnvironmentName -eq "uat-win") {
            Copy-Item (Join-Path $ReleaseRoot "backend\.env.uat") $BackendEnvPath -Force
        }
        else {
            Copy-Item (Join-Path $ReleaseRoot "backend\.env.prod") $BackendEnvPath -Force
        }

        if ($FrontendEnvContent.Trim().Length -gt 0) {
            Set-Content -Path $FrontendEnvPath -Value $FrontendEnvContent -Encoding UTF8
        }
        elseif ($EnvironmentName -eq "uat-win") {
            Copy-Item (Join-Path $ReleaseRoot "frontend\.env.uat") $FrontendEnvPath -Force
        }
        else {
            Copy-Item (Join-Path $ReleaseRoot "frontend\.env.prod") $FrontendEnvPath -Force
        }
    }

    Invoke-Step "Install backend dependencies" {
        $PythonCommand = Get-PythonCommand
        $ReleaseBackendDir = Join-Path $ReleaseRoot "backend"
        $VenvDir = Join-Path $ReleaseBackendDir ".venv"
        Invoke-Python $PythonCommand @("-m", "venv", $VenvDir)

        $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r (Join-Path $ReleaseBackendDir "requirements.txt")
        & $VenvPython -m compileall (Join-Path $ReleaseBackendDir "app")
    }

    Invoke-Step "Install frontend dependencies and build" {
        $ReleaseFrontendDir = Join-Path $ReleaseRoot "frontend"
        Push-Location $ReleaseFrontendDir
        try {
            Invoke-NodeScript install
            Invoke-NodeScript build
        }
        finally {
            Pop-Location
        }
    }

    Invoke-Step "Promote release to current" {
        if (Test-Path $CurrentRoot) {
            Remove-Item $CurrentRoot -Recurse -Force
        }
        Copy-Item -Path $ReleaseRoot -Destination $CurrentRoot -Recurse -Force
    }

    if ($EnvironmentName -eq "uat-win") {
        if ([string]::IsNullOrWhiteSpace($BackendServiceName)) {
            $BackendServiceName = "TranscriptionTemplateBackendUAT"
        }
        if ([string]::IsNullOrWhiteSpace($FrontendServiceName)) {
            $FrontendServiceName = "TranscriptionTemplateFrontendUAT"
        }
    }
    else {
        if ([string]::IsNullOrWhiteSpace($BackendServiceName)) {
            $BackendServiceName = "TranscriptionTemplateBackendProd"
        }
        if ([string]::IsNullOrWhiteSpace($FrontendServiceName)) {
            $FrontendServiceName = "TranscriptionTemplateFrontendProd"
        }
    }

    Invoke-Step "Restart services" {
        Restart-AppServices -BackendName $BackendServiceName -FrontendName $FrontendServiceName
    }

    Write-Host ""
    Write-Host "Deployment complete: $CurrentRoot"
}

switch ($Command) {
    "win-dev" { Start-WinDev }
    "uat-win" { Deploy-Win -EnvironmentName "uat-win" }
    "prod-win" { Deploy-Win -EnvironmentName "prod-win" }
    default { Show-Help }
}
