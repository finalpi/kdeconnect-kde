# SPDX-License-Identifier: GPL-3.0-only
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PayloadDirectory,
    [Parameter(Mandatory=$true)][string]$Destination
)
$ErrorActionPreference = 'Stop'
try {
    if (-not [Environment]::Is64BitProcess) { throw 'Run this installer from 64-bit PowerShell.' }
    $payload = [IO.Path]::GetFullPath($PayloadDirectory)
    $target = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
    if (-not [IO.Path]::IsPathRooted($Destination) -or $target -eq [IO.Path]::GetPathRoot($target).TrimEnd('\') -or
        $target -eq $env:WINDIR -or $target -eq $env:ProgramFiles -or $target.Contains('"')) {
        throw 'Choose an application directory, not a drive or system directory.'
    }
    $info = Get-Content -LiteralPath (Join-Path $payload 'fork-build.json') -Raw | ConvertFrom-Json
    $base = Join-Path $payload 'official.exe'
    $component = Join-Path $payload 'kdeconnect_clipboard.dll'
    if ((Get-FileHash -LiteralPath $base -Algorithm SHA256).Hash -ne $info.baseInstallerSha256 -or
        (Get-FileHash -LiteralPath $component -Algorithm SHA256).Hash -ne $info.componentSha256) {
        throw 'Installer payload failed its SHA-256 check.'
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $base
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*K Desktop Environment*') {
        throw 'Official base installer signature is invalid.'
    }
    $previous = Join-Path $target 'bin\kdeconnect\kdeconnect_clipboard.dll'
    if (Test-Path -LiteralPath $previous) {
        $backup = Join-Path $env:LOCALAPPDATA ('kdeconnect-fork-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
        New-Item -ItemType Directory -Path $backup | Out-Null
        Copy-Item -LiteralPath $previous -Destination (Join-Path $backup 'kdeconnect_clipboard.dll')
        Write-Output "Previous component backed up: $backup"
    }
    # Only stop this installation's KDE processes. User configuration is untouched.
    $names = 'kdeconnect*','dbus-daemon'
    Get-Process -Name $names -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase)
    } | Stop-Process -Force
    $process = Start-Process -FilePath $base -ArgumentList ('/S /D=' + $target) -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Official base installation failed: $($process.ExitCode)" }
    $core = Join-Path $target 'bin\kdeconnectcore.dll'
    if ((Get-FileHash -LiteralPath $core -Algorithm SHA256).Hash -ne $info.runtimeCoreSha256) {
        throw 'Installed core does not match the fork ABI.'
    }
    # The base installer may launch the indicator on some versions. Stop it before replacement.
    Get-Process -Name $names -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and $_.Path.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase)
    } | Stop-Process -Force
    Copy-Item -LiteralPath $component -Destination $previous -Force
    Copy-Item -LiteralPath (Join-Path $payload 'fork-build.json') -Destination (Join-Path $target 'fork-build.json') -Force
    if ((Get-FileHash -LiteralPath $previous -Algorithm SHA256).Hash -ne $info.componentSha256) {
        throw 'Installed fork component failed verification.'
    }
    # Keep the upstream uninstaller, shell integration and single uninstall entry.
    $registry = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry32)
    $uninstall = $registry.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall\KDE Connect', $true)
    if ($uninstall) {
        $uninstall.SetValue('DisplayVersion', $info.forkVersion)
        $uninstall.SetValue('DisplayName', 'KDE Connect (Native Clipboard Fork)')
        $uninstall.SetValue('URLInfoAbout', $info.sourceRepository)
        $uninstall.Dispose()
    }
    $registry.Dispose()
    Write-Output "KDE Connect $($info.forkVersion) installed successfully. Pairing configuration preserved."
    Write-Output 'Launch KDE Connect from the existing Start menu shortcut.'
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
