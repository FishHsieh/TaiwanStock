param(
    [Parameter(Mandatory = $true)]
    [string]$WorkDir,
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [Parameter(Mandatory = $true)]
    [string]$FirebaseCliExe,
    [Parameter(Mandatory = $false)]
    [string]$GoogleWorkspaceScript = '',
    [Parameter(Mandatory = $false)]
    [string]$MarketDataFile = '',
    [Parameter(Mandatory = $false)]
    [string]$FinalArticleFile = '',
    [Parameter(Mandatory = $false)]
    [string]$GoogleWorkspaceStateFile = '',
    [Parameter(Mandatory = $false)]
    [string]$NodePortableDir = '',
    [Parameter(Mandatory = $false)]
    [string]$SyncLogFile = ''
)

$ErrorActionPreference = 'Continue'
Set-StrictMode -Version Latest
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -LiteralPath $WorkDir

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

if ($NodePortableDir -and (Test-Path -LiteralPath $NodePortableDir)) {
    $env:PATH = $NodePortableDir + ';' + $env:PATH
}

if (-not $SyncLogFile) {
    $syncLogRoot = Join-Path $WorkDir 'Reports'
    $SyncLogFile = Join-Path $syncLogRoot ("post_report_sync_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
}

$syncLogDir = Split-Path -Parent $SyncLogFile
if ($syncLogDir -and -not (Test-Path -LiteralPath $syncLogDir)) {
    New-Item -ItemType Directory -Path $syncLogDir -Force | Out-Null
}

$transcriptStarted = $false
try {
    Start-Transcript -Path $SyncLogFile -Force | Out-Null
    $transcriptStarted = $true
}
catch {
    Write-Warning ('Background sync transcript failed: ' + $_.Exception.Message)
}

try {
    if (Test-Path -LiteralPath $FirebaseCliExe) {
        Write-Host '=== Deploying Firebase Hosting ==='
        & $FirebaseCliExe deploy --only hosting --non-interactive
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'Firebase deploy failed.'
        }
        else {
            Write-Host 'Firebase deploy completed.'
        }
    }
    else {
        Write-Warning ('Could not find Firebase CLI: ' + $FirebaseCliExe)
    }
}
finally {
    if ($transcriptStarted) {
        try {
            Stop-Transcript | Out-Null
        }
        catch {
            Write-Warning ('Background sync transcript stop failed: ' + $_.Exception.Message)
        }
    }
}
