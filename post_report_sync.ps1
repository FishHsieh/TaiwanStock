param(
    [Parameter(Mandatory = $true)]
    [string]$WorkDir,
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [Parameter(Mandatory = $true)]
    [string]$GoogleWorkspaceScript,
    [Parameter(Mandatory = $true)]
    [string]$MarketDataFile,
    [Parameter(Mandatory = $true)]
    [string]$FinalArticleFile,
    [Parameter(Mandatory = $true)]
    [string]$FirebaseCliExe,
    [Parameter(Mandatory = $true)]
    [string]$GoogleWorkspaceStateFile,
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

$GoogleWorkspaceConfigFile = Join-Path $WorkDir 'google_workspace.local.ps1'
if (Test-Path -LiteralPath $GoogleWorkspaceConfigFile) {
    try {
        . $GoogleWorkspaceConfigFile
    }
    catch {
        Write-Warning ('Google Workspace local config load failed: ' + $GoogleWorkspaceConfigFile)
    }
}

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
    if (Test-Path -LiteralPath $GoogleWorkspaceScript) {
        Write-Host '=== Background sync: publishing Google Workspace artifacts ==='
        & $PythonExe $GoogleWorkspaceScript --market-data $MarketDataFile --final-article $FinalArticleFile --title 'TaiwanStockBot 盤中市場報告' --state-file $GoogleWorkspaceStateFile
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'Google Workspace sync failed in background; continuing to Firebase deploy.'
        }
    }
    else {
        Write-Warning ('Could not find Google Workspace sync script: ' + $GoogleWorkspaceScript)
    }

    if (Test-Path -LiteralPath $FirebaseCliExe) {
        Write-Host '=== Background sync: deploying Firebase Hosting ==='
        & $FirebaseCliExe deploy --only hosting --non-interactive
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'Firebase deploy failed in background.'
        }
        else {
            Write-Host 'Firebase deploy completed in background.'
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
