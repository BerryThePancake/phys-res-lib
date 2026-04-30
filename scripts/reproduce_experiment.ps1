# Reproduce synthetic shift-study runs (prints seeds and metrics to stdout).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
New-Item -ItemType Directory -Force "artifacts" | Out-Null
$env:PYTHONHASHSEED = "0"
python -m pip install -r "python\requirements.txt"
python "python\shift_study.py" --seed 0 --json-out "artifacts\run_seed0.json"
python "python\shift_study.py" --seed 1 --visible-buses 16 --json-out "artifacts\run_fullobs_seed1.json"
Write-Host "Done. See artifacts\*.json"
