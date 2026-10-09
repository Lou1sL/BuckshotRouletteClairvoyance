[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$GameDirectory,
    [string]$PackageDirectory = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$pvGameDir = (Resolve-Path -LiteralPath $GameDirectory).ProviderPath
$pvGameExe = Join-Path $pvGameDir 'Buckshot Roulette.exe'
$pvCandidate = Join-Path $PackageDirectory 'Buckshot Roulette.ProbabilityVision.exe'
$pvManifestPath = Join-Path $PackageDirectory 'build-verification.json'
$pvManifest = Get-Content -LiteralPath $pvManifestPath -Raw | ConvertFrom-Json
$pvExpectedPatch = [string]$pvManifest.output_sha256
$pvOldHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $pvGameExe).Hash.ToLowerInvariant()
$pvAllowedSource = @(
    'df2f8a31bd469438a1a29f831945ccea7b26963ab735f73b32936792207b1663',
    '0432c9b3233c89dbeff984b18b7d35dee34d2e269fd6f8f5e2d7babbdd86f072',
    '39ece519b5807a1191e5972d2ccfbcacec3841cbc10d9733e3c85c1ab050266c'
)
if ($pvOldHash -eq $pvExpectedPatch) {
    Write-Output 'Probability Vision is already installed; no changes made.'
    return
}
if ($pvOldHash -notin $pvAllowedSource) { throw 'Unsupported or updated game EXE. Do not overwrite it with this version.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvCandidate).Hash.ToLowerInvariant() -ne $pvExpectedPatch) { throw 'Candidate EXE hash mismatch.' }
if (@(Get-Process | Where-Object { $_.ProcessName -like '*Buckshot*' }).Count -gt 0) { throw 'Close Buckshot Roulette first.' }

$pvStamp = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(8)).ToString('yyyyMMdd-HHmmss')
$pvSuffix = [Guid]::NewGuid().ToString('N').Substring(0, 6)
$pvBackup = Join-Path $pvGameDir ('Buckshot Roulette.exe.before-probability-vision-' + $pvStamp + '-' + $pvSuffix)
$pvStage = Join-Path $pvGameDir ('Buckshot Roulette.exe.probability-vision-pending-' + $pvSuffix)
$pvReceipt = Join-Path $pvGameDir ('ProbabilityVision-install-' + $pvStamp + '-' + $pvSuffix + '.json')
foreach ($pvPath in @($pvBackup, $pvStage, $pvReceipt)) {
    if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($pvPath)) -ne $pvGameDir) { throw 'Invalid installation target.' }
    if (Test-Path -LiteralPath $pvPath) { throw 'A destination already exists.' }
}
if (-not $PSCmdlet.ShouldProcess($pvGameExe, 'Back up current EXE and install Probability Vision')) { return }

[IO.File]::Copy($pvGameExe, $pvBackup, $false)
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvBackup).Hash.ToLowerInvariant() -ne $pvOldHash) { throw 'Backup verification failed; main EXE unchanged.' }
[IO.File]::Copy($pvCandidate, $pvStage, $false)
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvStage).Hash.ToLowerInvariant() -ne $pvExpectedPatch) { throw 'Staging verification failed; main EXE unchanged.' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvGameExe).Hash.ToLowerInvariant() -ne $pvOldHash) { throw 'Main EXE changed during installation; stopped.' }
if (@(Get-Process | Where-Object { $_.ProcessName -like '*Buckshot*' }).Count -gt 0) { throw 'Game started during installation; stopped.' }
[IO.File]::Replace($pvStage, $pvGameExe, [System.Management.Automation.Language.NullString]::Value)
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pvGameExe).Hash.ToLowerInvariant() -ne $pvExpectedPatch) { throw "Installed EXE hash mismatch. Restore backup: $pvBackup" }

$pvReceiptData = [ordered]@{ game_exe=$pvGameExe; backup=$pvBackup; original_sha256=$pvOldHash; installed_sha256=$pvExpectedPatch; installed_at=[DateTimeOffset]::UtcNow.ToString('o') }
$pvReceiptData | ConvertTo-Json | Out-File -LiteralPath $pvReceipt -Encoding utf8
Write-Output ('Installed Probability Vision. Backup: ' + $pvBackup)
Write-Output 'To customize the HUD, copy probability_vision.cfg next to the game EXE; an existing config is never overwritten.'
