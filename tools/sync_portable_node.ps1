[CmdletBinding()]
param(
    [string]$SourceDir
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ToolsDir = (Resolve-Path -LiteralPath (Split-Path -Parent $PSCommandPath)).Path
$DestinationDir = Join-Path $ToolsDir 'nodejs'
$StagingDir = Join-Path $ToolsDir '.nodejs-staging'
$VersionFile = Join-Path $DestinationDir 'VERSION.txt'

function Assert-UnderToolsDir {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($ToolsDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path must stay within tools/: $fullPath"
    }

    return $fullPath
}

function Get-DefaultNodeSourceDir {
    $preferredRoots = @(
        'C:\Program Files\nodejs',
        'C:\Program Files (x86)\nodejs'
    )

    foreach ($candidate in $preferredRoots) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'node.exe')) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $nodeCommand = Get-Command node -ErrorAction Stop
    $nodeDir = Split-Path -Parent $nodeCommand.Source
    return (Resolve-Path -LiteralPath $nodeDir).Path
}

if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    $SourceDir = Get-DefaultNodeSourceDir
}
else {
    $SourceDir = (Resolve-Path -LiteralPath $SourceDir).Path
}

$DestinationDir = Assert-UnderToolsDir -Path $DestinationDir
$StagingDir = Assert-UnderToolsDir -Path $StagingDir

$sourceNodeExe = Join-Path $SourceDir 'node.exe'
$sourceNpmCmd = Join-Path $SourceDir 'npm.cmd'
if (-not (Test-Path -LiteralPath $sourceNodeExe)) {
    throw "Source Node installation is missing node.exe: $SourceDir"
}
if (-not (Test-Path -LiteralPath $sourceNpmCmd)) {
    throw "Source Node installation is missing npm.cmd: $SourceDir"
}

if ($SourceDir.TrimEnd('\') -ieq $DestinationDir.TrimEnd('\')) {
    throw 'Source and destination are the same path.'
}

$destinationLeaf = Split-Path -Leaf $DestinationDir
$backupDir = Assert-UnderToolsDir -Path (Join-Path $ToolsDir ('.nodejs-backup-' + (Get-Date -Format 'yyyyMMdd_HHmmss')))
$backupLeaf = Split-Path -Leaf $backupDir

if (Test-Path -LiteralPath $StagingDir) {
    Remove-Item -LiteralPath $StagingDir -Recurse -Force
}

New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
Write-Host "Copying portable Node from $SourceDir to $StagingDir"
& robocopy $SourceDir $StagingDir /MIR /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null
$robocopyExit = $LASTEXITCODE
if ($robocopyExit -ge 8) {
    throw "robocopy failed with exit code $robocopyExit"
}

if (-not (Test-Path -LiteralPath (Join-Path $StagingDir 'node.exe'))) {
    throw 'Staging copy is missing node.exe.'
}
if (-not (Test-Path -LiteralPath (Join-Path $StagingDir 'npm.cmd'))) {
    throw 'Staging copy is missing npm.cmd.'
}

$hadDestination = Test-Path -LiteralPath $DestinationDir
try {
    if ($hadDestination) {
        if (Test-Path -LiteralPath $backupDir) {
            Remove-Item -LiteralPath $backupDir -Recurse -Force
        }
        Rename-Item -LiteralPath $DestinationDir -NewName $backupLeaf -ErrorAction Stop
    }

    Rename-Item -LiteralPath $StagingDir -NewName $destinationLeaf -ErrorAction Stop

    $portableNodeExe = Join-Path $DestinationDir 'node.exe'
    $version = (& $portableNodeExe -v).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
        throw 'Portable Node verification failed.'
    }

    Set-Content -LiteralPath $VersionFile -Encoding ASCII -Value @(
        "Version: $version"
        "Source: $SourceDir"
        "Updated: $(Get-Date -Format o)"
    )

    if ($hadDestination -and (Test-Path -LiteralPath $backupDir)) {
        Remove-Item -LiteralPath $backupDir -Recurse -Force
    }

    Write-Host "Portable Node updated to $version"
    Write-Host "Version file written to $VersionFile"
}
catch {
    if (Test-Path -LiteralPath $DestinationDir) {
        Remove-Item -LiteralPath $DestinationDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($hadDestination -and (Test-Path -LiteralPath $backupDir)) {
        Rename-Item -LiteralPath $backupDir -NewName $destinationLeaf -ErrorAction SilentlyContinue
    }

    throw
}
