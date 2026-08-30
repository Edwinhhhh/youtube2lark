$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $SystemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $SystemPython) {
        throw "Python is not available on PATH. Install Python 3.10+ first."
    }

    & $SystemPython.Source -m venv (Join-Path $ProjectRoot ".venv")
}

& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
& $Python -m yt2feishu.web

