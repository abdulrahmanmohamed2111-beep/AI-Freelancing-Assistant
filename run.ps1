$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    $projectPython = Join-Path $PSScriptRoot '../../work/venv/Scripts/python.exe'
}
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Create the Python environment using the README instructions first.'
}
& $projectPython -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
