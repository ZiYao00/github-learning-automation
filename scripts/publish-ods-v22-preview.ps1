# ODS V2.2 single-note preview publisher. Run locally by double-clicking the .cmd file.
# Copies ONLY the reviewed preview and its two reading-media files. Never overwrites.
# Research Packet, existing formal ODS notes and the source project stay untouched.
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$settingsFile = Join-Path $projectRoot 'config\local.json'
if (-not (Test-Path -LiteralPath $settingsFile -PathType Leaf)) {
  throw 'Missing config/local.json'
}
$settings = Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $settings.vault_root -or -not $settings.notes_subdir) {
  throw 'This publisher requires the configured vault_root and notes_subdir.'
}
$vault = [IO.Path]::GetFullPath([string]$settings.vault_root)
$subdir = [string]$settings.notes_subdir
if ([IO.Path]::IsPathRooted($subdir) -or $subdir -match '(^|[\\/])\.\.($|[\\/])') {
  throw 'Invalid notes_subdir in local config.'
}
if (-not (Test-Path -LiteralPath (Join-Path $vault '.obsidian') -PathType Container)) {
  throw 'The configured Vault has no .obsidian directory. No file was copied.'
}
$targetRoot = [IO.Path]::GetFullPath((Join-Path $vault $subdir))
$vaultWithSep = $vault.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
if (-not $targetRoot.StartsWith($vaultWithSep,[StringComparison]::OrdinalIgnoreCase)) {
  throw 'notes_subdir resolves outside Vault.'
}

$pendingFolder = '00-' + [char]0x5F85 + [char]0x6574 + [char]0x7406
$sourceInbox = Join-Path $projectRoot ('notes\github\' + $pendingFolder)
$candidates = @(Get-ChildItem -LiteralPath $sourceInbox -File -Filter '*V2.2*.md')
if ($candidates.Count -ne 1) {
  throw ('Expected exactly one V2.2 Markdown preview; found ' + $candidates.Count)
}
$preview = $candidates[0]
$sourceData = Join-Path $projectRoot 'notes\github\_repo-data\Osmantic\ODS'
$items = @(
  @{ Source=$preview.FullName; Relative=(Join-Path $pendingFolder $preview.Name) },
  @{ Source=(Join-Path $sourceData 'media\readme-first-f9c72d216f56.png'); Relative='_repo-data\Osmantic\ODS\media\readme-first-f9c72d216f56.png' },
  @{ Source=(Join-Path $sourceData 'readme-first-9e59b2b86c96.json'); Relative='_repo-data\Osmantic\ODS\readme-first-9e59b2b86c96.json' }
)

# Preflight the entire bundle. A changed existing file blocks all writes.
foreach ($item in $items) {
  $source = [string]$item.Source
  $dest = [IO.Path]::GetFullPath((Join-Path $targetRoot ([string]$item.Relative)))
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw ('Missing source: ' + $source) }
  $rootWithSep = $targetRoot.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
  if (-not $dest.StartsWith($rootWithSep,[StringComparison]::OrdinalIgnoreCase)) {
    throw ('Destination is outside note root: ' + $dest)
  }
  if (Test-Path -LiteralPath $dest) {
    if (-not (Test-Path -LiteralPath $dest -PathType Leaf)) { throw ('Blocked non-file: ' + $dest) }
    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    $destHash = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
    if ($sourceHash -ne $destHash) {
      throw ('Refusing to overwrite a different file: ' + $dest)
    }
  }
}

foreach ($item in $items) {
  $source = [string]$item.Source
  $dest = [IO.Path]::GetFullPath((Join-Path $targetRoot ([string]$item.Relative)))
  if ($CheckOnly) {
    Write-Host ('CHECK OK: ' + $dest)
    continue
  }
  if (-not (Test-Path -LiteralPath $dest)) {
    $parent = Split-Path -Parent $dest
    if (-not (Test-Path -LiteralPath $parent)) {
      New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $source -Destination $dest -ErrorAction Stop
    Write-Host ('COPIED: ' + $dest)
  } else {
    Write-Host ('UNCHANGED: ' + $dest)
  }
  if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash) {
    throw ('Hash verification failed: ' + $dest)
  }
}
if (-not $CheckOnly) {
  Write-Host ('READY: Open the V2.2 preview under ' + (Join-Path $targetRoot $pendingFolder))
}

