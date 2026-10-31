param([string]$Binary = (Join-Path $PSScriptRoot 'bin/WorkbenchD7.exe'))
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$validationRoot = Join-Path $root ('evidence/validation-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $validationRoot | Out-Null
$cases = @('all','initial','correct','regression')
$checks = @()
function Invoke-Fixture([string]$component, [string]$caseName, [string]$fileName) {
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo.FileName = $Binary
    $p.StartInfo.Arguments = '--component ' + $component + ' --case ' + $caseName
    $p.StartInfo.WorkingDirectory = $validationRoot
    $p.StartInfo.UseShellExecute = $false
    $p.StartInfo.CreateNoWindow = $true
    $p.StartInfo.RedirectStandardOutput = $true
    $p.StartInfo.RedirectStandardError = $true
    $null = $p.Start()
    $stdoutTask = $p.StandardOutput.ReadToEndAsync()
    $stderrTask = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit(10000)) { $p.Kill(); $p.Dispose(); throw 'Fixture timeout' }
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $exitCode = $p.ExitCode
    $p.Dispose()
    [System.IO.File]::WriteAllText((Join-Path $validationRoot $fileName), $stdout, (New-Object System.Text.UTF8Encoding($false)))
    if ($exitCode -ne 0) { throw ('Fixture failed: ' + $stderr) }
    return ($stdout | ConvertFrom-Json)
}
function Check([string]$id, [bool]$ok) {
    $script:checks += [pscustomobject]@{id=$id;status=$(if ($ok) {'pass'} else {'fail'})}
}
$first = Invoke-Fixture 'D0007/C0322-02' 'all' 'run-1.json'
$second = Invoke-Fixture 'D0007/C0322-02' 'all' 'run-2.json'
Check 'fresh_rerun_identical' ((Get-FileHash -LiteralPath (Join-Path $validationRoot 'run-1.json')).Hash -eq (Get-FileHash -LiteralPath (Join-Path $validationRoot 'run-2.json')).Hash)
Check 'all_38_original_diagnostics_pass' (@($first.checks).Count -eq 38 -and @($first.checks | Where-Object status -ne 'pass').Count -eq 0)
Check 'actual_method_calls' ($first.metrics.method_calls -eq 42)
Check 'regression_rejected_with_7_of_11_preserved' ($first.records.regression.accepted -eq $false -and $first.records.regression.p2p_preserved -eq 7 -and $first.records.regression.p2p_total -eq 11)
Check 'correct_accepted_with_11_of_11_preserved' ($first.records.correct.accepted -eq $true -and $first.records.correct.p2p_preserved -eq 11)
Check 'regression_repairs_all_3_failing_tests' (($first.records.totals | Where-Object variant -eq 'regression' | Measure-Object F2P_passed -Sum).Sum -eq 3)
$mappings = @{'inputs'='raw-inputs.json';'observations'='raw-outcomes.json';'diagnostics'='diagnostics.json';'correct'='correct-trace.json';'regression'='regression-trace.json';'totals'='totals.json'}
foreach ($entry in $mappings.GetEnumerator()) {
    $historical = Get-Content -LiteralPath (Join-Path $root ('historical/'+$entry.Value)) -Raw | ConvertFrom-Json
    # Property order is immaterial; recursively sort JSON object properties for deep comparisons.
    $current = $first.records.($entry.Key)
    function StableValue($value) {
        if ($null -eq $value) { return $null }
        if ($value -is [System.Management.Automation.PSCustomObject]) {
            $ordered = [ordered]@{}
            foreach ($property in ($value.PSObject.Properties.Name | Sort-Object)) { $ordered[$property] = StableValue $value.$property }
            return $ordered
        }
        if ($value -is [array]) { return ,@($value | ForEach-Object { StableValue $_ }) }
        return $value
    }
    $a = ConvertTo-Json -InputObject (StableValue $historical) -Depth 100 -Compress
    $b = ConvertTo-Json -InputObject (StableValue $current) -Depth 100 -Compress
    Check ('historical_'+$entry.Key+'_identical') ($a -ceq $b)
}
foreach ($caseName in $cases) {
    $result = Invoke-Fixture 'D0007/C0322-02' $caseName ('case-'+$caseName+'.json')
    Check ('case_'+$caseName+'_execution') ($result.execution -eq 'pass')
    if ($caseName -eq 'correct') { Check 'correct_candidate_accepted' ($result.candidate_accepted -eq $true) }
    if ($caseName -eq 'initial' -or $caseName -eq 'regression') { Check ($caseName+'_candidate_not_accepted') ($result.candidate_accepted -eq $false) }
}
$pairOne = Invoke-Fixture 'D0007/C0322-01' 'all' 'pair-one.json'
Check 'pair01_supported' ($pairOne.component_id -eq 'D0007/C0322-01' -and $pairOne.execution -eq 'pass')
foreach ($args in @(@('--component','D0007/C0322-99'),@('--component','D0007/C0322-02','--case','unknown'),@('--component','D0007/C0322-02','--output','escape'),@('--component','D0007/C0322-02','--component','D0007/C0322-02'))) {
    $null = & $Binary @args 2>&1
    Check ('reject_'+($args -join '_')) ($LASTEXITCODE -eq 2)
}
$sources = Get-Content -LiteralPath (Join-Path $root 'SOURCE-MANIFEST.json') -Raw | ConvertFrom-Json
foreach ($source in $sources) {
    Check ('copied_source_unchanged_'+$source.destination) ((Get-FileHash -LiteralPath (Join-Path $root $source.destination)).Hash.ToLowerInvariant() -eq $source.sha256)
}
$report = [ordered]@{schema_version='1.0.0';binary=$Binary;binary_sha256=(Get-FileHash -LiteralPath $Binary).Hash.ToLowerInvariant();validation_directory=$validationRoot;checks=$checks;result=$(if (@($checks | Where-Object status -eq 'fail').Count -eq 0) {'pass'} else {'fail'});scientific_validation='unverified';scope='frozen authored C0322 fixture only'}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $validationRoot 'VALIDATION.json') -Encoding utf8
$report | ConvertTo-Json -Depth 8
if ($report.result -ne 'pass') { exit 1 }
