#Requires -Version 5.1
<#
.SYNOPSIS
  AURA launcher – Windows equivalent of scripts/macos/aura.sh
.DESCRIPTION
  Manages the FastAPI backend, Next.js frontend, and competitor collectors.
  Commands: clean, build, start, dev, up, stop, intel, menu.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ────────────────────────────────────────────────────────────────────
$RootDir = (Resolve-Path "$PSScriptRoot\..\..").Path
$ApiDir = Join-Path $RootDir "api"
$WebDir = Join-Path $RootDir "web"
$CompetitorDir = Join-Path $RootDir "competitor-intelligence"
$CompetitorComposeFile = Join-Path $CompetitorDir "compose.yaml"
$RunDir = Join-Path $RootDir ".aura\run"
$LogDir = Join-Path $RootDir ".aura\logs"
$LocalUvCache = Join-Path $RootDir ".aura\uv-cache"
$LocalBunCache = Join-Path $RootDir ".aura\bun-cache"
$AuraTmpDir = Join-Path $RootDir ".aura\tmp"

$extraPaths = @(
    "$env:USERPROFILE\.local\bin",
    "$env:USERPROFILE\.bun\bin",
    "$env:LOCALAPPDATA\uv\bin",
    "$env:APPDATA\uv\bin"
)
foreach ($p in $extraPaths) {
    if ($p -and (Test-Path $p) -and ($env:Path -notlike "*$p*")) {
        $env:Path = "$p;$env:Path"
    }
}

$script:ApiHost = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$script:ApiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$script:WebPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { "3000" }
$script:UvCacheDir = if ($env:UV_CACHE_DIR) { $env:UV_CACHE_DIR } else { $LocalUvCache }
$script:BunCacheDir = if ($env:BUN_INSTALL_CACHE_DIR) { $env:BUN_INSTALL_CACHE_DIR } else { $LocalBunCache }
$script:CompetitorEnabled = if ($env:AURA_COMPETITOR_INTELLIGENCE) { $env:AURA_COMPETITOR_INTELLIGENCE } else { "true" }
$script:CompetitorRequired = if ($env:AURA_COMPETITOR_REQUIRED) { $env:AURA_COMPETITOR_REQUIRED } else { "true" }
$script:CompetitorDiscovery = if ($env:AURA_COMPETITOR_DISCOVERY) { $env:AURA_COMPETITOR_DISCOVERY } else { "true" }
$script:ChangeDetectionPort = if ($env:CHANGEDETECTION_PORT) { $env:CHANGEDETECTION_PORT } else { "5001" }
$script:SearxngPort = if ($env:SEARXNG_PORT) { $env:SEARXNG_PORT } else { "8080" }
$script:RssHubPort = if ($env:RSSHUB_PORT) { $env:RSSHUB_PORT } else { "1200" }

$ApiPidFile = Join-Path $RunDir "api.pid"
$WebPidFile = Join-Path $RunDir "web.pid"
$ApiLog = Join-Path $LogDir "api.log"
$ApiErrLog = Join-Path $LogDir "api_err.log"
$WebLog = Join-Path $LogDir "web.log"
$WebErrLog = Join-Path $LogDir "web_err.log"

function Log($msg) {
    Write-Host "[aura] $msg"
}

function Fail($msg) {
    throw "[aura] ERROR: $msg"
}

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Fail "Missing '$name'. Install it before running this command."
    }
}

function Get-JsPackageManager {
    if (Get-Command "bun" -ErrorAction SilentlyContinue) { return "bun" }
    if (Get-Command "npm" -ErrorAction SilentlyContinue) { return "npm" }
    Fail "No JavaScript package manager found. Install bun (https://bun.sh) or Node.js npm."
}

function Get-PythonCommand {
    if (Get-Command "python" -ErrorAction SilentlyContinue) { return "python" }
    if (Get-Command "py" -ErrorAction SilentlyContinue) { return "py" }
    return $null
}

function Require-Tools {
    Require-Command "uv"
    $null = Get-JsPackageManager
    if (-not (Get-Command "curl.exe" -ErrorAction SilentlyContinue)) {
        Fail "curl.exe not found. It ships with Windows 10 (1803+). Please update Windows or install curl manually."
    }
}

function Ensure-Layout {
    New-Item -ItemType Directory -Path $RunDir, $LogDir, $AuraTmpDir -Force | Out-Null
}

function Read-ProcId($procIdFile) {
    if (-not (Test-Path $procIdFile)) { return $null }
    $content = (Get-Content $procIdFile -Raw).Trim()
    if ($content -match '^\d+$') { return [int]$content }
    return $null
}

function Get-ProcessCommand([int]$procId) {
    try {
        $row = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if ($row -and $row.CommandLine) { return $row.CommandLine }
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) { return $proc.ProcessName }
    } catch { }
    return "unknown"
}

function Get-ListenerProcIds([string]$port) {
    $ids = New-Object System.Collections.Generic.List[int]
    $lines = @(netstat -ano 2>$null | Select-String "LISTENING" | Where-Object { $_.Line -match ":$port\s" })
    foreach ($line in $lines) {
        $parts = ($line.ToString().Trim()) -split '\s+'
        $foundId = $parts[-1]
        if ($foundId -match '^\d+$') { [void]$ids.Add([int]$foundId) }
    }
    return @($ids | Select-Object -Unique)
}

function Port-IsBusy([string]$port) {
    $ids = @(Get-ListenerProcIds $port)
    return $ids.Count -gt 0
}

function Describe-PortHolder([string]$port) {
    $ids = @(Get-ListenerProcIds $port)
    if ($ids.Count -eq 0) { return "unknown process" }
    $procId = $ids[0]
    return "pid $procId ($(Get-ProcessCommand $procId))"
}

function Stop-ProcessTree([int]$procId) {
    try {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc -and -not $proc.HasExited) {
            & taskkill /PID $procId /T /F 2>$null | Out-Null
        }
    } catch { }
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

function Stop-PortListener($name, [string]$port) {
    $ids = @(Get-ListenerProcIds $port)
    if ($ids.Count -eq 0) { return }

    foreach ($procId in $ids) {
        Log "Stopping $name listener on port $port (pid $procId)"
        Stop-ProcessTree $procId
    }

    for ($i = 0; $i -lt 20; $i++) {
        if (-not (Port-IsBusy $port)) { return }
        Start-Sleep -Milliseconds 250
    }

    foreach ($procId in @(Get-ListenerProcIds $port)) {
        Log "$name on port $port did not stop cleanly; force killing pid $procId ($(Get-ProcessCommand $procId))"
        Stop-ProcessTree $procId
    }
}

function Test-DockerCompose {
    if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) { return $false }
    & docker info 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) { return $false }
    & docker compose version 1>$null 2>$null
    return $LASTEXITCODE -eq 0
}

function Invoke-CompetitorCompose {
    $dockerArgs = @(
        "compose",
        "--env-file", (Join-Path $RootDir ".env"),
        "-f", $CompetitorComposeFile,
        "--project-directory", $CompetitorDir,
        "--profile", "discovery",
        "--profile", "social"
    ) + @($args)
    & docker @dockerArgs
}

function Import-CompetitorApiKey {
    if ($env:CHANGEDETECTION_API_KEY) { return }
    $code = "import json; print(json.load(open('/datastore/changedetection.json'))['settings']['application']['api_access_token'])"
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $token = Invoke-CompetitorCompose exec -T changedetection python -c $code 2>$null | Select-Object -Last 1
    } catch {
        $token = $null
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
    if ($token) {
        $token = "$token".Trim()
    }
    if ($token) {
        $env:CHANGEDETECTION_API_KEY = $token
        Log "Loaded the changedetection API credential."
    } else {
        Log "Changedetection API credential was not available; watch provisioning will be skipped."
    }
}

function Start-CompetitorSupport {
    if ($script:CompetitorEnabled -ne "true") {
        Log "Competitor intelligence support is disabled (AURA_COMPETITOR_INTELLIGENCE=$($script:CompetitorEnabled))."
        return
    }

    if (-not (Test-DockerCompose)) {
        if ($script:CompetitorRequired -eq "true") {
            Fail "Competitor intelligence requires Docker Compose. Set AURA_COMPETITOR_INTELLIGENCE=false to run AURA without collectors."
        }
        Log "Docker Compose is unavailable; starting AURA without competitor collectors."
        return
    }

    Log "Starting competitor collectors: changedetection, browser, SearXNG, RSSHub, and Redis."
    $services = @("up", "-d", "changedetection")
    if ($script:CompetitorDiscovery -eq "true") {
        $services += @("searxng", "rsshub-redis", "rsshub")
    }
    Invoke-CompetitorCompose @services
    if ($LASTEXITCODE -ne 0) {
        if ($script:CompetitorRequired -eq "true") {
            Fail "Competitor collector services failed to start."
        }
        Log "Competitor collector services failed to start; continuing without them."
        return
    }

    if (-not (Wait-ForHttp "changedetection" "http://127.0.0.1:$($script:ChangeDetectionPort)/" 90)) {
        if ($script:CompetitorRequired -eq "true") {
            Invoke-CompetitorCompose logs --tail=40 changedetection | Out-Host
            Fail "Changedetection did not become ready."
        }
        Log "Changedetection is not ready; direct website scans remain available."
    }

    if ($script:CompetitorDiscovery -eq "true") {
        if (-not (Wait-ForHttp "SearXNG" "http://127.0.0.1:$($script:SearxngPort)/" 45)) {
            Log "SearXNG is not ready; search will remain disabled."
        }
        if (-not (Wait-ForHttp "RSSHub" "http://127.0.0.1:$($script:RssHubPort)/healthz" 60)) {
            Log "RSSHub is not ready; feed polling will remain limited."
        }
        if (-not $env:SEARXNG_URL) {
            $env:SEARXNG_URL = "http://127.0.0.1:$($script:SearxngPort)"
        }
    }

    if (-not $env:AURA_COMPETITOR_REFRESH) { $env:AURA_COMPETITOR_REFRESH = "true" }
    if (-not $env:CHANGEDETECTION_API_URL) {
        $env:CHANGEDETECTION_API_URL = "http://127.0.0.1:$($script:ChangeDetectionPort)"
    }
    if (-not $env:INTEL_WEBHOOK_HOST) {
        $env:INTEL_WEBHOOK_HOST = "host.docker.internal:$($script:ApiPort)"
    }
    Import-CompetitorApiKey
}

function Stop-CompetitorSupport {
    if ($script:CompetitorEnabled -ne "true") { return }
    if (-not (Test-Path $CompetitorComposeFile)) { return }
    if (-not (Test-DockerCompose)) { return }
    Log "Stopping competitor collector services (data volumes are preserved)."
    Invoke-CompetitorCompose down --remove-orphans | Out-Null
}

function Invoke-CompetitorWatchProvision {
    if ($script:CompetitorEnabled -ne "true") { return }
    if (-not $env:CHANGEDETECTION_API_KEY) { return }
    $python = Get-PythonCommand
    if (-not $python) {
        Log "Python is unavailable; competitor watch provisioning was skipped."
        return
    }

    Log "Provisioning competitor watches into changedetection."
    if (-not $env:INTEL_WEBHOOK_HOST) {
        $env:INTEL_WEBHOOK_HOST = "host.docker.internal:$($script:ApiPort)"
    }
    if (-not $env:CHANGEDETECTION_API_URL) {
        $env:CHANGEDETECTION_API_URL = "http://127.0.0.1:$($script:ChangeDetectionPort)"
    }
    Push-Location $CompetitorDir
    try {
        & $python -m competitor_intelligence provision-changedetection
        if ($LASTEXITCODE -ne 0) {
            Log "Competitor watch provisioning failed; the native AURA dashboard is still available."
        }
    } finally {
        Pop-Location
    }
}

function Stop-Stack {
    Stop-TrackedProcess "frontend" $WebPidFile
    Stop-TrackedProcess "backend" $ApiPidFile
    Stop-PortListener "frontend" $script:WebPort
    Stop-PortListener "backend" $script:ApiPort
    Stop-CompetitorSupport
}

function Capture-ListenerProcId($name, $port, $procIdFile) {
    $ids = @(Get-ListenerProcIds $port)
    if ($ids.Count -gt 0) {
        Set-Content -Path $procIdFile -Value $ids[0]
        Log "Tracking $name listener (pid $($ids[0]))"
    }
}

function Assert-PortsFree {
    if (Port-IsBusy $script:ApiPort) {
        Fail "Port $($script:ApiPort) is still in use by $(Describe-PortHolder $script:ApiPort) after stop."
    }
    if (Port-IsBusy $script:WebPort) {
        Fail "Port $($script:WebPort) is still in use by $(Describe-PortHolder $script:WebPort) after stop."
    }
}

function Import-LauncherEnv {
    $envFile = Join-Path $RootDir ".env"
    $allowed = @(
        "API_HOST",
        "API_PORT",
        "WEB_PORT",
        "AURA_COMPETITOR_INTELLIGENCE",
        "AURA_COMPETITOR_REQUIRED",
        "AURA_COMPETITOR_DISCOVERY",
        "AURA_COMPETITOR_REFRESH",
        "CHANGEDETECTION_PORT",
        "SEARXNG_PORT",
        "RSSHUB_PORT"
    )
    foreach ($line in Get-Content $envFile) {
        $trimmed = "$line".Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        $name, $value = $trimmed.Split("=", 2)
        $name = $name.Trim()
        if ($allowed -notcontains $name) { continue }
        $value = $value.Trim().Trim('"').Trim("'")
        if ($value) { Set-Item -Path "Env:$name" -Value $value }
    }

    if ($env:API_HOST) { $script:ApiHost = $env:API_HOST }
    if ($env:API_PORT) { $script:ApiPort = $env:API_PORT }
    if ($env:WEB_PORT) { $script:WebPort = $env:WEB_PORT }
    if ($env:AURA_COMPETITOR_INTELLIGENCE) { $script:CompetitorEnabled = $env:AURA_COMPETITOR_INTELLIGENCE }
    if ($env:AURA_COMPETITOR_REQUIRED) { $script:CompetitorRequired = $env:AURA_COMPETITOR_REQUIRED }
    if ($env:AURA_COMPETITOR_DISCOVERY) { $script:CompetitorDiscovery = $env:AURA_COMPETITOR_DISCOVERY }
    if ($env:CHANGEDETECTION_PORT) { $script:ChangeDetectionPort = $env:CHANGEDETECTION_PORT }
    if ($env:SEARXNG_PORT) { $script:SearxngPort = $env:SEARXNG_PORT }
    if ($env:RSSHUB_PORT) { $script:RssHubPort = $env:RSSHUB_PORT }
}

function Ensure-Env {
    if (-not (Test-Path (Join-Path $RootDir ".env"))) {
        Fail "Missing .env. Copy .env.example to .env and configure DB_ENGINE or the MySQL variables before starting AURA."
    }
    Import-LauncherEnv

    $webEnvLocal = Join-Path $WebDir ".env.local"
    if (-not (Test-Path $webEnvLocal)) {
        $exampleTxt = Join-Path $WebDir "env.example.txt"
        if (Test-Path $exampleTxt) {
            Log "Creating web/.env.local from the non-secret template"
            Copy-Item $exampleTxt $webEnvLocal
        } else {
            Log "Creating minimal web/.env.local"
            Set-Content -Path $webEnvLocal -Value "NEXT_PUBLIC_API_URL=http://localhost:$($script:ApiPort)"
        }
    }
}

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

    Get-ChildItem -Path $ApiDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ApiDir -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue

    if ($script:UvCacheDir -eq $LocalUvCache -and (Test-Path $LocalUvCache)) {
        Remove-Item -Recurse -Force $LocalUvCache -ErrorAction SilentlyContinue
    }

    Log "Preserved source, dependencies, env files, and database data"
}

function Build-Backend {
    Log "Syncing backend environment"
    Push-Location $ApiDir
    try {
        $env:UV_CACHE_DIR = $script:UvCacheDir
        & uv sync --frozen
        if ($LASTEXITCODE -ne 0) { Fail "Backend sync failed" }

        Log "Compiling backend sources"
        & uv run python -m compileall main.py db.py schemas.py graph.py routes agents services
        if ($LASTEXITCODE -ne 0) { Fail "Backend compile failed" }
    } finally {
        Pop-Location
    }
}

function Build-Frontend {
    Log "Installing frontend lockfile dependencies"
    Push-Location $WebDir
    try {
        $jsPm = Get-JsPackageManager
        if ($jsPm -eq "bun") {
            $env:HUSKY = "0"
            $env:BUN_INSTALL_CACHE_DIR = $script:BunCacheDir
            & bun install --frozen-lockfile
            if ($LASTEXITCODE -ne 0) { Fail "Frontend install (bun) failed" }

            Log "Running frontend typecheck"
            & bun run typecheck
            if ($LASTEXITCODE -ne 0) { Fail "Frontend typecheck failed" }

            Log "Building frontend"
            & bun run build
            if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed" }
        } else {
            Log "bun was not found; using npm. The macOS launcher requires bun."
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

function Wait-ForHttp($name, $url, $maxAttempts = 120) {
    for ($i = 0; $i -lt $maxAttempts; $i++) {
        try {
            & curl.exe --silent --show-error --fail --max-time 10 $url 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                Log "$name is ready at $url"
                return $true
            }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Start-Processes($frontendMode) {
    Require-Tools
    Ensure-Env
    if ($frontendMode -eq "production") {
        Ensure-ProductionBuild
    }
    Ensure-Layout
    Stop-Stack
    Assert-PortsFree
    Start-CompetitorSupport

    foreach ($lf in @($ApiLog, $ApiErrLog, $WebLog, $WebErrLog)) {
        Set-Content -Path $lf -Value "" -Force
    }

    Log "Starting backend on http://localhost:$($script:ApiPort)"
    $env:UV_CACHE_DIR = $script:UvCacheDir
    $apiProc = Start-Process -FilePath "uv" `
        -ArgumentList "run uvicorn main:app --host $($script:ApiHost) --port $($script:ApiPort)" `
        -WorkingDirectory $ApiDir `
        -RedirectStandardOutput $ApiLog `
        -RedirectStandardError $ApiErrLog `
        -PassThru -WindowStyle Hidden
    Set-Content -Path $ApiPidFile -Value $apiProc.Id

    Log "Starting frontend on http://localhost:$($script:WebPort)"
    $env:PORT = $script:WebPort
    if (-not $env:NEXT_PUBLIC_API_URL) {
        $env:NEXT_PUBLIC_API_URL = "http://localhost:$($script:ApiPort)"
    }

    $jsPm = Get-JsPackageManager
    if ($jsPm -eq "bun") {
        $webExe = "bun.exe"
        $devArgs = "run dev"
        $prodArgs = "run start"
    } else {
        $webExe = "npm.cmd"
        $devArgs = "run dev"
        $prodArgs = "run start"
    }
    $webArgs = if ($frontendMode -eq "production") { $prodArgs } else { $devArgs }

    $webProc = Start-Process -FilePath $webExe `
        -ArgumentList $webArgs `
        -WorkingDirectory $WebDir `
        -RedirectStandardOutput $WebLog `
        -RedirectStandardError $WebErrLog `
        -PassThru -WindowStyle Hidden
    Set-Content -Path $WebPidFile -Value $webProc.Id

    if (-not (Wait-ForHttp "backend" "http://localhost:$($script:ApiPort)/api/health" 120)) {
        Log "Backend failed to become ready. Recent log:"
        if (Test-Path $ApiErrLog) { Get-Content $ApiErrLog -Tail 40 | Write-Host }
        if (Test-Path $ApiLog) { Get-Content $ApiLog -Tail 20 | Write-Host }
        Stop-Stack
        Fail "Backend did not start in time."
    }
    Capture-ListenerProcId "backend" $script:ApiPort $ApiPidFile
    Invoke-CompetitorWatchProvision

    if (-not (Wait-ForHttp "frontend" "http://localhost:$($script:WebPort)/dashboard/studio" 180)) {
        Log "Frontend failed to become ready. Recent log:"
        if (Test-Path $WebErrLog) { Get-Content $WebErrLog -Tail 40 | Write-Host }
        if (Test-Path $WebLog) { Get-Content $WebLog -Tail 20 | Write-Host }
        Capture-ListenerProcId "frontend" $script:WebPort $WebPidFile
        Stop-Stack
        Fail "Frontend did not start in time."
    }
    Capture-ListenerProcId "frontend" $script:WebPort $WebPidFile

    Log "AURA is running. Logs: $ApiLog and $WebLog"
    Log "Press Ctrl-C to stop both processes"

    try {
        while ($true) {
            $apiAlive = $false
            $webAlive = $false
            $apiId = Read-ProcId $ApiPidFile
            $webId = Read-ProcId $WebPidFile
            if ($null -ne $apiId) {
                $api = Get-Process -Id $apiId -ErrorAction SilentlyContinue
                if ($null -ne $api -and -not $api.HasExited) { $apiAlive = $true }
            }
            if ($null -ne $webId) {
                $web = Get-Process -Id $webId -ErrorAction SilentlyContinue
                if ($null -ne $web -and -not $web.HasExited) { $webAlive = $true }
            }
            if (-not $apiAlive -or -not $webAlive) {
                Log "One process exited. Recent backend log:"
                if (Test-Path $ApiErrLog) { Get-Content $ApiErrLog -Tail 20 | Write-Host }
                if (Test-Path $ApiLog) { Get-Content $ApiLog -Tail 10 | Write-Host }
                Log "Recent frontend log:"
                if (Test-Path $WebErrLog) { Get-Content $WebErrLog -Tail 20 | Write-Host }
                if (Test-Path $WebLog) { Get-Content $WebLog -Tail 10 | Write-Host }
                Stop-Stack
                break
            }
            Start-Sleep -Seconds 1
        }
    } finally {
        Stop-Stack
    }
}

function Show-Usage {
    Write-Host @"

Usage: .\scripts\windows\aura.ps1 <command>

Commands:
  clean   Remove generated build output, Python caches, runner logs/PIDs, and local uv cache
  build   Clean generated output, install locked dependencies, typecheck, and build both apps
  start   Start FastAPI, competitor collectors, and the existing Next.js production build
  dev     Start FastAPI, competitor collectors, and Next.js in development mode
  up      Clean, build, then start FastAPI and Next.js in production mode
  stop    Stop AURA processes, free the API/web ports, and stop collector containers
  intel   Start the full application stack (competitor intelligence is built in)

"@
}

function Show-Menu {
    Write-Host ""
    Write-Host "AURA launcher"
    Write-Host "============"
    Write-Host "1) Build only"
    Write-Host "2) Build + run"
    Write-Host "3) Just run"
    Write-Host "4) Dev mode (hot reload)"
    Write-Host "q) Exit"
    Write-Host ""

    $choice = Read-Host "Choose an option [1-4/q]"
    switch ($choice) {
        "1" { Clean-Generated; Build-Stack }
        "2" { Clean-Generated; Build-Stack; Start-Processes "production" }
        "3" { Start-Processes "production" }
        "4" { Start-Processes "development" }
        { $_ -in "q", "Q", "" } { Log "Nothing started" }
        default { Fail "Unknown option '$choice'. Choose 1, 2, 3, 4, or q." }
    }
}

if (Test-Path (Join-Path $RootDir ".env")) {
    Import-LauncherEnv
}

switch ($Command) {
    { $_ -in "", "menu" } { Show-Menu }
    "clean" { Clean-Generated }
    "build" { Clean-Generated; Build-Stack }
    "start" { Start-Processes "production" }
    "dev" { Start-Processes "development" }
    { $_ -in "intel", "intelligence" } {
        Log "Competitor Intelligence is integrated into AURA; starting the full application stack."
        Start-Processes "production"
    }
    "up" { Clean-Generated; Build-Stack; Start-Processes "production" }
    "stop" { Stop-Stack }
    { $_ -in "-h", "--help", "help" } { Show-Usage }
    default { Show-Usage; exit 2 }
}
