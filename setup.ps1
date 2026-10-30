# Tutorial Studio setup (Windows). Safe to run again any time (e.g. after moving this folder).
#   powershell -ExecutionPolicy Bypass -File setup.ps1 [-Agent claude|gemini|codex|all]

param([string]$Agent = "all")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "Machine")
}

function Ensure-Tool($command, $wingetId, $label) {
    if (Get-Command $command -ErrorAction SilentlyContinue) {
        Write-Host "[ok] $label" -ForegroundColor Green
        return
    }
    Write-Host "[..] Installing $label with winget" -ForegroundColor Yellow
    winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
}

Write-Host "`n== 1. Tools ==" -ForegroundColor Cyan
Ensure-Tool ffmpeg Gyan.FFmpeg "FFmpeg"
Ensure-Tool node OpenJS.NodeJS.LTS "Node.js"
Ensure-Tool py Python.Python.3.12 "Python"
$nodeMajor = [int]((node --version).TrimStart("v").Split(".")[0])
if ($nodeMajor -lt 22) { throw "The Kokoro voice (hyperframes) needs Node.js 22+, you have $(node --version). Run: winget upgrade OpenJS.NodeJS.LTS" }

Write-Host "`n== 2. Python environment ==" -ForegroundColor Cyan
$py = ".venv\Scripts\python.exe"
$healthy = (Test-Path $py) -and ((& $py -c "print(1)" 2>$null) -eq "1")
if (-not $healthy) {
    if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
    py -3 -m venv .venv
}
& $py -m pip install --upgrade pip -q
& $py -m pip install -r requirements.txt -q

Write-Host "`n== 3. Browser for filming ==" -ForegroundColor Cyan
$edge = & $py -c "from playwright.sync_api import sync_playwright as s`nwith s() as p:`n  try: p.chromium.launch(channel='msedge').close(); print('ok')`n  except Exception: print('no')"
if ($edge -ne "ok") { & $py -m playwright install chromium } else { Write-Host "[ok] Microsoft Edge" -ForegroundColor Green }

Write-Host "`n== 4. Voice model (Kokoro, ~330 MB, first run only) ==" -ForegroundColor Cyan
$env:HYPERFRAMES_PYTHON = (Resolve-Path $py).Path
"Ready." | Set-Content -Encoding utf8 "$env:TEMP\tts-test.txt"
npx --yes hyperframes@0.8.172 tts "$env:TEMP\tts-test.txt" -o "$env:TEMP\tts-test.wav"

Write-Host "`n== 5. Skills and sub-agents for your AI agent ==" -ForegroundColor Cyan
& $py scripts\install_agent.py --agent $Agent

Write-Host "`n== 6. Check ==" -ForegroundColor Cyan
& $py scripts\doctor.py --quick
Write-Host "`nAll set. Open this folder in your AI agent and say: 'Make a tutorial of <app> showing how to <task>'" -ForegroundColor Green
