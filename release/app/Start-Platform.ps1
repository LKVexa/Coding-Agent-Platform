param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PlatformArguments)
$ErrorActionPreference = 'Stop'
$candidates = @()
if ($env:CODING_AGENT_PYTHON) { $candidates += $env:CODING_AGENT_PYTHON }
$profileFolder = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
$candidates += Join-Path $profileFolder '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$foundPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($foundPython) { $candidates += $foundPython.Source }
$selectedPython = $null
foreach ($candidate in $candidates) {
    if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and ($candidate -notlike '*WindowsApps*')) {
        $selectedPython = $candidate
        break
    }
}
if (-not $selectedPython) {
    Write-Error 'Python is required. Set CODING_AGENT_PYTHON to Python 3.12.14; see START_HERE.md.'
    exit 2
}
if (-not $PlatformArguments) { $PlatformArguments = @('doctor') }
& $selectedPython -I -B (Join-Path $PSScriptRoot 'agent.py') @PlatformArguments
exit $LASTEXITCODE
