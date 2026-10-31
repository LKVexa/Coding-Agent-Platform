param([string]$Destination = ('builds/build-' + [guid]::NewGuid().ToString('N')))
$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($PSScriptRoot)
if ([System.IO.Path]::IsPathRooted($Destination) -or $Destination.Contains(':') -or ($Destination -split '[/\\]' -contains '..')) { throw 'Destination must be a relative contained path' }
$buildRoot = [System.IO.Path]::GetFullPath((Join-Path $root $Destination))
if (-not $buildRoot.StartsWith($root.TrimEnd('\') + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Build path escapes package' }
if (Test-Path -LiteralPath $buildRoot) { throw 'Refusing to overwrite an existing build directory' }
$cursor = Get-Item -LiteralPath $root
while ($null -ne $cursor) {
    if (($cursor.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse package root rejected' }
    $cursor = $cursor.Parent
}
foreach ($row in (Get-Content -LiteralPath (Join-Path $root 'SOURCE-MANIFEST.json') -Raw | ConvertFrom-Json)) {
    $path = Join-Path $root $row.destination
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw ('Pinned source mismatch: ' + $row.destination) }
}
$windowsRoot = [Environment]::GetFolderPath([Environment+SpecialFolder]::Windows)
$compiler = Join-Path $windowsRoot 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { $compiler = Join-Path $windowsRoot 'Microsoft.NET/Framework/v4.0.30319/csc.exe' }
if (-not (Test-Path -LiteralPath $compiler)) { throw '.NET Framework C# compiler not installed' }
New-Item -ItemType Directory -Path $buildRoot | Out-Null
$binary = Join-Path $buildRoot 'WorkbenchD7.exe'
$compilerArgs = @('/nologo','/langversion:5','/target:exe','/main:WorkbenchAdapter','/r:System.Web.Extensions.dll',('/out:'+$binary),(Join-Path $root 'src/HarnessCommon.cs'),(Join-Path $root 'src/P2PDiagnostics.cs'),(Join-Path $root 'src/WorkbenchAdapter.cs'))
$compileOutput = & $compiler @compilerArgs 2>&1
$compileCode = $LASTEXITCODE
$receipt = [ordered]@{schema_version='1.0.0';executable=$compiler;arguments=$compilerArgs;cwd=$root;compiler_version=(Get-Item -LiteralPath $compiler).VersionInfo.FileVersion;compiler_sha256=(Get-FileHash -LiteralPath $compiler).Hash.ToLowerInvariant();exit_code=$compileCode;output=@($compileOutput | ForEach-Object { $_.ToString() });binary=$binary}
if (Test-Path -LiteralPath $binary) { $receipt.binary_sha256=(Get-FileHash -LiteralPath $binary).Hash.ToLowerInvariant() }
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $buildRoot 'BUILD.json') -Encoding utf8
if ($compileCode -ne 0) { throw ('Compiler failed: ' + ($compileOutput -join "`n")) }
$receipt | ConvertTo-Json -Depth 8
