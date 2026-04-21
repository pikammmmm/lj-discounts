$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,
        [string[]] $Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    $created = $false

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & $pyLauncher.Source -3 -m venv .venv
        $created = ($LASTEXITCODE -eq 0)
    }

    if (-not $created) {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($python) {
            & $python.Source -m venv .venv
            $created = ($LASTEXITCODE -eq 0)
        }
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "Python 3 was not found. Install Python from https://www.python.org/downloads/windows/ or use the packaged Windows zip from GitHub Actions/Releases."
    }
}

Invoke-Checked $venvPython @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked $venvPython @("-m", "pip", "install", "-r", "requirements.txt")
Invoke-Checked $venvPython @("run.py", "--open")
