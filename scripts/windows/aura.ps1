#Requires -Version 5.1
<#
.SYNOPSIS
  AURA launcher – Windows equivalent of scripts/macos/aura.sh
.DESCRIPTION
  Manages the FastAPI backend and Next.js frontend on Windows.
  Commands: clean, build, start, dev, up, stop, menu (interactive).
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("clean", "build", "start", "dev", "up", "stop", "menu", "help", "")]
    [string]$Command = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ────────────────────────────────────────────────────────────────────
$RootDir    = (Resolve-Path "$PSScriptRoot\..\..").Path
$ApiDir     = Join-Path $RootDir "api"
$WebDir     = Join-Path $RootDir "web"
$RunDir     = Join-Path $RootDir ".aura\run"
$LogDir     = Join-Path $RootDir ".aura\logs"
$LocalUvCache  = Join-Path $RootDir ".aura\uv-cache"
$LocalBunCache = Join-Path $RootDir ".aura\bun-cache"
$AuraTmpDir    = Join-Path $RootDir ".aura\tmp"

# ── PATH bootstrap (resolve uv and bun regardless of whether they are on the
#    system PATH – add the standard per-user install locations first) ──────────
$extraPaths = @(
    "$env:USERPROFILE\.local\bin",   # uv default install location
    "$env:USERPROFILE\.bun\bin",     # bun default install location
    "$env:LOCALAPPDATA\uv\bin",      # uv alternate install on Windows
    "$env:APPDATA\uv\bin"            # uv alternate install on Windows
)
foreach ($p in $extraPaths) {
    if ($p -and (Test-Path $p) -and ($env:Path -notlike "*$p*")) {
        $env:Path = "$p;$env:Path"
    }
}

$ApiHost = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$WebPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { "3000" }
$UvCacheDir  = if ($env:UV_CACHE_DIR)           { $env:UV_CACHE_DIR }           else { $LocalUvCache }
$BunCacheDir = if ($env:BUN_INSTALL_CACHE_DIR)  { $env:BUN_INSTALL_CACHE_DIR }  else { $LocalBunCache }

$ApiPidFile = Join-Path $RunDir "api.pid"
$WebPidFile = Join-Path $RunDir "web.pid"
$ApiLog     = Join-Path $LogDir "api.log"
$ApiErrLog  = Join-Path $LogDir "api_err.log"
$WebLog     = Join-Path $LogDir "web.log"
$WebErrLog  = Join-Path $LogDir "web_err.log"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Log($msg) {
    Write-Host "[aura] $msg"
}

function Fail($msg) {
    # Use a terminating exception instead of exit 1, so that Pop-Location in
    # finally blocks still runs before the script ends.
    throw "[aura] ERROR: $msg"
}

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Fail "Missing '$name'. Install it before running this command."
    }
}

# Detect the best available JS package manager: bun > npm
function Get-JsPackageManager {
    if (Get-Command "bun" -ErrorAction SilentlyContinue) { return "bun" }
    if (Get-Command "npm" -ErrorAction SilentlyContinue) { return "npm" }
    Fail "No JavaScript package manager found. Install bun (https://bun.sh) or Node.js npm."
}

function Require-Tools {
    Require-Command "uv"
    # At least one of bun or npm must be present
    $null = Get-JsPackageManager
    # curl.exe (native Windows, always present on Win10 1803+)
    if (-not (Get-Command "curl.exe" -ErrorAction SilentlyContinue)) {
        Fail "curl.exe not found. It ships with Windows 10 (1803+). Please update Windows or install curl manually."
    }
}

function Ensure-Layout {
    New-Item -ItemType Directory -Path $RunDir, $LogDir, $AuraTmpDir -Force | Out-Null
}

# ── PID / process management ────────────────────────────────────────────────

function Read-ProcId($procIdFile) {
    if (-not (Test-Path $procIdFile)) { return $null }
    $content = (Get-Content $procIdFile -Raw).Trim()
    if ($content -match '^\d+$') { return [int]$content }
    return $null
}

function Get-ListenerProcId($port) {
    # Use netstat to find the PID listening on a given port
    $lines = netstat -ano 2>$null | Select-String "LISTENING" |
        Where-Object { $_ -match ":$port\s" }
    if ($lines) {
        $parts = ($lines[0].ToString().Trim()) -split '\s+'
        $foundId = $parts[-1]
        if ($foundId -match '^\d+$') { return [int]$foundId }
    }
    return $null
}

function Port-IsBusy($port) {
    return $null -ne (Get-ListenerProcId $port)
}

function Stop-ProcessTree($procId) {
    # Kill the process and all children via taskkill /T
    try {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc -and -not $proc.HasExited) {
            # /T = kill child processes, /F = force
            & taskkill /PID $procId /T /F 2>$null | Out-Null
        }
    } catch {
        # Process already gone – that's fine
    }
}

function Stop-TrackedProcess($name, $procIdFile) {
    $procId = Read-ProcId $procIdFile
    if ($null -eq $procId) {
        Remove-Item $procIdFile -ErrorAction SilentlyContinue
        return
    }

    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($null -eq $proc -or $proc.HasExited) {
        Remove-Item $procIdFile -ErrorAction SilentlyContinue
        return
    }

    Log "Stopping $name (pid $procId)"
    Stop-ProcessTree $procId

    # Wait up to 5 seconds for exit
    for ($i = 0; $i -lt 20; $i++) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($null -eq $proc -or $proc.HasExited) { break }
        Start-Sleep -Milliseconds 250
    }

    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($null -ne $proc -and -not $proc.HasExited) {
        Log "$name did not stop cleanly; force killing pid $procId"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }

    Remove-Item $procIdFile -ErrorAction SilentlyContinue
}

function Stop-Stack {
    Stop-TrackedProcess "frontend" $WebPidFile
    Stop-TrackedProcess "backend"  $ApiPidFile
}

function Capture-ListenerProcId($name, $port, $procIdFile) {
    $procId = Get-ListenerProcId $port
    if ($null -ne $procId) {
        Set-Content -Path $procIdFile -Value $procId
        Log "Tracking $name listener (pid $procId)"
    }
}

# ── Assert ports ─────────────────────────────────────────────────────────────

function Assert-PortsFree {
    if (Port-IsBusy $ApiPort) {
        Fail "Port $ApiPort is already in use. Run '.\scripts\windows\stop.ps1' for AURA-owned processes or stop the other process manually."
    }
    if (Port-IsBusy $WebPort) {
        Fail "Port $WebPort is already in use. Run '.\scripts\windows\stop.ps1' for AURA-owned processes or stop the other process manually."
    }
}

# ── Env ──────────────────────────────────────────────────────────────────────

function Ensure-Env {
    if (-not (Test-Path (Join-Path $RootDir ".env"))) {
        Fail "Missing .env. Copy .env.example to .env and set DATABASE_URL before starting AURA."
    }

    $webEnvLocal = Join-Path $WebDir ".env.local"
    if (-not (Test-Path $webEnvLocal)) {
        $exampleTxt = Join-Path $WebDir "env.example.txt"
        if (Test-Path $exampleTxt) {
            Log "Creating web/.env.local from the non-secret template"
            Copy-Item $exampleTxt $webEnvLocal
        } else {
            # Create a minimal .env.local so Next.js doesn't complain
            Log "Creating minimal web/.env.local"
            Set-Content -Path $webEnvLocal -Value "NEXT_PUBLIC_API_URL=http://localhost:$ApiPort"
        }
    }
}

# ── Clean ────────────────────────────────────────────────────────────────────

function Clean-Generated {
    Stop-Stack
    Log "Removing generated build and runner output only"

    $pathsToRemove = @(
        (Join-Path $WebDir ".next"),
        (Join-Path $WebDir "tsconfig.tsbuildinfo"),
        $RunDir,
        $LogDir,
        $AuraTmpDir,
        $LocalBunCache
    )

    foreach ($p in $pathsToRemove) {
        if (Test-Path $p) {
            Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue
        }
    }

    # Remove Python caches
    Get-ChildItem -Path $ApiDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ApiDir -Recurse -File -Include "*.pyc","*.pyo" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue

    if ($UvCacheDir -eq $LocalUvCache -and (Test-Path $LocalUvCache)) {
        Remove-Item -Recurse -Force $LocalUvCache -ErrorAction SilentlyContinue
    }

    Log "Preserved source, dependencies, env files, and database data"
}

# ── Build ────────────────────────────────────────────────────────────────────

function Build-Backend {
    Log "Syncing backend environment"
    Push-Location $ApiDir
    try {
        $env:UV_CACHE_DIR = $UvCacheDir
        & uv sync --frozen
        if ($LASTEXITCODE -ne 0) { Fail "Backend sync failed" }

        Log "Compiling backend sources"
        & uv run python -m compileall main.py db.py schemas.py graph.py routes agents
        if ($LASTEXITCODE -ne 0) { Fail "Backend compile failed" }
    } finally {
        Pop-Location
    }
}

function Build-Frontend {
    Log "Installing frontend dependencies"
    Push-Location $WebDir
    try {
        $jsPm = Get-JsPackageManager

        if ($jsPm -eq "bun") {
            $env:BUN_INSTALL_CACHE_DIR = $BunCacheDir
            & bun install
            if ($LASTEXITCODE -ne 0) { Fail "Frontend install (bun) failed" }

            Log "Running frontend typecheck"
            & bun run typecheck
            if ($LASTEXITCODE -ne 0) { Fail "Frontend typecheck failed" }

            Log "Building frontend"
            & bun run build
            if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed" }
        } else {
            & npm install --prefer-offline
            if ($LASTEXITCODE -ne 0) { Fail "Frontend install (npm) failed" }

            Log "Running frontend typecheck"
            & npm run typecheck
            if ($LASTEXITCODE -ne 0) { Fail "Frontend typecheck failed" }

            Log "Building frontend"
            & npm run build
            if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed" }
        }
    } finally {
        Pop-Location
    }
}

function Build-Stack {
    Require-Tools
    Ensure-Layout
    Build-Backend
    Build-Frontend
    Log "Build completed"
}

function Ensure-ProductionBuild {
    $buildId = Join-Path $WebDir ".next\BUILD_ID"
    if (-not (Test-Path $buildId)) {
        Fail "No frontend production build found. Choose 'Build + run' or run '.\scripts\windows\build.ps1' first."
    }
}

# ── HTTP wait ────────────────────────────────────────────────────────────────

function Wait-ForHttp($name, $url, $maxAttempts = 120) {
    # 120 × 500 ms = 60 s – enough for Next.js first-compile on a slow machine
    for ($i = 0; $i -lt $maxAttempts; $i++) {
        try {
            $null = curl.exe --silent --show-error --fail --max-time 5 $url 2>$null
            if ($LASTEXITCODE -eq 0) {
                Log "$name is ready at $url"
                return $true
            }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# ── Start ────────────────────────────────────────────────────────────────────

function Start-Processes($frontendMode) {
    Require-Tools
    Ensure-Env
    if ($frontendMode -eq "production") {
        Ensure-ProductionBuild
    }
    Ensure-Layout
    Stop-Stack
    Assert-PortsFree

    $jsPm = Get-JsPackageManager

    # Clear / initialise all log files so each run starts clean
    foreach ($lf in @($ApiLog, $ApiErrLog, $WebLog, $WebErrLog)) {
        Set-Content -Path $lf -Value "" -Force
    }

    # ── Start backend ──
    Log "Starting backend on http://localhost:$ApiPort"

    $env:UV_CACHE_DIR = $UvCacheDir
    $apiProc = Start-Process -FilePath "uv" `
        -ArgumentList "run uvicorn main:app --host $ApiHost --port $ApiPort" `
        -WorkingDirectory $ApiDir `
        -RedirectStandardOutput $ApiLog `
        -RedirectStandardError $ApiErrLog `
        -PassThru -WindowStyle Hidden

    Set-Content -Path $ApiPidFile -Value $apiProc.Id

    # ── Start frontend ──
    Log "Starting frontend on http://localhost:$WebPort"

    $env:PORT = $WebPort
    if (-not $env:NEXT_PUBLIC_API_URL) {
        $env:NEXT_PUBLIC_API_URL = "http://localhost:$ApiPort"
    }

    # Resolve the executable and args based on available package manager
    if ($jsPm -eq "bun") {
        $webExe  = "bun"
        $devArgs = "run dev"
        $prodArgs = "run start"
    } else {
        $webExe  = "npm"
        $devArgs = "run dev"
        $prodArgs = "run start"
    }

    if ($frontendMode -eq "production") {
        $webArgs = $prodArgs
    } else {
        $webArgs = $devArgs
    }

    $webProc = Start-Process -FilePath $webExe `
        -ArgumentList $webArgs `
        -WorkingDirectory $WebDir `
        -RedirectStandardOutput $WebLog `
        -RedirectStandardError $WebErrLog `
        -PassThru -WindowStyle Hidden

    Set-Content -Path $WebPidFile -Value $webProc.Id

    # ── Wait for readiness ──
    # Backend is fast; 60 attempts = 30 s
    if (-not (Wait-ForHttp "backend" "http://localhost:$ApiPort/api/health" 60)) {
        Log "Backend failed to become ready. Recent log:"
        if (Test-Path $ApiErrLog) { Get-Content $ApiErrLog -Tail 40 | Write-Host }
        if (Test-Path $ApiLog)    { Get-Content $ApiLog -Tail 20  | Write-Host }
        Stop-Stack
        Fail "Backend did not start in time."
    }
    Capture-ListenerProcId "backend" $ApiPort $ApiPidFile

    # Frontend first-compile can be slow; 180 attempts = 90 s
    if (-not (Wait-ForHttp "frontend" "http://localhost:$WebPort/dashboard/overview" 180)) {
        Log "Frontend failed to become ready. Recent log:"
        if (Test-Path $WebErrLog) { Get-Content $WebErrLog -Tail 40 | Write-Host }
        if (Test-Path $WebLog)    { Get-Content $WebLog -Tail 20    | Write-Host }
        Capture-ListenerProcId "frontend" $WebPort $WebPidFile
        Stop-Stack
        Fail "Frontend did not start in time."
    }
    Capture-ListenerProcId "frontend" $WebPort $WebPidFile

    Log "AURA is running. Logs: $ApiLog and $WebLog"
    Log "Press Ctrl-C to stop both processes"

    # Register cleanup on Ctrl-C / PowerShell.Exiting
    try {
        [Console]::TreatControlCAsInput = $false
    } catch { }

    $null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
        Stop-Stack
    } -ErrorAction SilentlyContinue

    # Keep-alive loop – watch both processes
    try {
        while ($true) {
            $apiAlive = $false
            $webAlive = $false

            try {
                $a = Get-Process -Id (Read-ProcId $ApiPidFile) -ErrorAction SilentlyContinue
                if ($null -ne $a -and -not $a.HasExited) { $apiAlive = $true }
            } catch { }

            try {
                $w = Get-Process -Id (Read-ProcId $WebPidFile) -ErrorAction SilentlyContinue
                if ($null -ne $w -and -not $w.HasExited) { $webAlive = $true }
            } catch { }

            if (-not $apiAlive -or -not $webAlive) {
                Log "One process exited unexpectedly. Recent backend log:"
                if (Test-Path $ApiErrLog) { Get-Content $ApiErrLog -Tail 20 | Write-Host }
                if (Test-Path $ApiLog)    { Get-Content $ApiLog    -Tail 10 | Write-Host }
                Log "Recent frontend log:"
                if (Test-Path $WebErrLog) { Get-Content $WebErrLog -Tail 20 | Write-Host }
                if (Test-Path $WebLog)    { Get-Content $WebLog    -Tail 10 | Write-Host }
                Stop-Stack
                break
            }

            Start-Sleep -Seconds 1
        }
    } catch {
        # Ctrl-C or termination
        Stop-Stack
    }
}

# ── Usage ────────────────────────────────────────────────────────────────────

function Show-Usage {
    Write-Host @"

Usage: .\scripts\windows\aura.ps1 <command>

Commands:
  clean   Remove generated build output, Python caches, runner logs/PIDs, and local uv cache
  build   Clean generated output, install locked dependencies, typecheck, and build both apps
  start   Start FastAPI and the existing Next.js production build
  dev     Start FastAPI and Next.js in development mode with hot reload
  up      Clean, build, then start FastAPI and Next.js in production mode
  stop    Stop only AURA processes recorded by this runner

"@
}

# ── Interactive menu ─────────────────────────────────────────────────────────

function Interactive-Menu {
    Write-Host ""
    Write-Host "AURA launcher"
    Write-Host "============"
    Write-Host "1) Build only"
    Write-Host "2) Build + run"
    Write-Host "3) Just run"
    Write-Host "q) Exit"
    Write-Host ""

    $choice = Read-Host "Choose an option [1-3/q]"
    switch ($choice) {
        "1" {
            Clean-Generated
            Build-Stack
        }
        "2" {
            Clean-Generated
            Build-Stack
            Start-Processes "production"
        }
        "3" {
            Start-Processes "production"
        }
        { $_ -in "q", "Q", "" } {
            Log "Nothing started"
        }
        default {
            Fail "Unknown option '$choice'. Choose 1, 2, 3, or q."
        }
    }
}

# ── Main ─────────────────────────────────────────────────────────────────────

switch ($Command) {
    { $_ -in "", "menu" } { Interactive-Menu }
    "clean"               { Clean-Generated }
    "build"               { Clean-Generated; Build-Stack }
    "start"               { Start-Processes "production" }
    "dev"                 { Start-Processes "development" }
    "up"                  { Clean-Generated; Build-Stack; Start-Processes "production" }
    "stop"                { Stop-Stack }
    "help"                { Show-Usage }
    default               { Show-Usage; exit 2 }
}
