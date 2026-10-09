[CmdletBinding(SupportsShouldProcess = $true)]
param([Parameter(Mandatory = $true)][string]$Receipt)

$ErrorActionPreference = 'Stop'
$pvReceipt = Get-Content -LiteralPath $Receipt -Raw | ConvertFrom-Json
$pvTarget = (Resolve-Path -LiteralPath $pvReceipt.game_exe).ProviderPath
$pvBackup = (Resolve-Path -LiteralPath $pvReceipt.backup).ProviderPath
$pvDir = [IO.Path]::GetDirectoryName($pvTarget)
if ([IO.Path]::GetFileName($pvTarget) -ne 'Buckshot Roulette.exe' -or [IO.Path]::GetDirectoryName($pvBackup) -ne $pvDir) { throw 'Invalid restore targets.' }
if ([IO.Path]::GetFileName($pvBackup) -notlike 'Buckshot Roulette.exe.before-QE-*') { throw 'Not a Q+E backup.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvTarget).Hash.ToLowerInvariant() -ne $pvReceipt.installed_sha256) { throw 'Game EXE changed since installation; refusing to overwrite.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvBackup).Hash.ToLowerInvariant() -ne $pvReceipt.original_sha256) { throw 'Backup checksum mismatch.' }
if (@(Get-Process | Where-Object { $_.ProcessName -like '*Buckshot*' }).Count -gt 0) { throw 'Close Buckshot Roulette first.' }
if (-not $PSCmdlet.ShouldProcess($pvTarget, 'Restore pre-Q+E EXE, retaining current EXE and backup')) { return }
$pvSuffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
$pvStage = Join-Path $pvDir ('Buckshot Roulette.exe.restore-pending-' + $pvSuffix)
$pvRetained = Join-Path $pvDir ('Buckshot Roulette.exe.QE-restored-' + $pvSuffix)
[IO.File]::Copy($pvBackup, $pvStage, $false)
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvStage).Hash.ToLowerInvariant() -ne $pvReceipt.original_sha256) { throw 'Restore staging checksum mismatch.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvTarget).Hash.ToLowerInvariant() -ne $pvReceipt.installed_sha256) { throw 'Game EXE changed during restore; stopped.' }
if (@(Get-Process | Where-Object { $_.ProcessName -like '*Buckshot*' }).Count -gt 0) { throw 'Game started during restore; stopped.' }
[IO.File]::Replace($pvStage, $pvTarget, $pvRetained)
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvTarget).Hash.ToLowerInvariant() -ne $pvReceipt.original_sha256) { throw 'Restore verification failed.' }
Write-Output ('Restored pre-Q+E version. Combined EXE retained at ' + $pvRetained)
