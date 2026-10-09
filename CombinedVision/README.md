# Q / E / combined builds

The extended source supports three independently generated files from the same supported vanilla game copy:

- `q`: direct Q shell-order display, singleplayer and multiplayer host.
- `e`: E-only conditional probability HUD.
- `combined`: both features, isolated input/display/state.

This repository contains **MOD code and patch tools only**. You supply the supported, licensed vanilla game EXE. No premodified Q/E executable, original game resource dump, Steam DLL, installed backup or local installation record is needed or distributed.

## Coexistence

Q uses its own CanvasLayer/Label and responds only to a non-repeat Q press. It displays `>` followed by 1=live / 0=blank for three seconds, refreshing against actual remaining order while visible. It does not overwrite game dialogue.

E starts hidden and toggles independently. Opening, refreshing or timing out Q does not change E's model or visibility; E toggling does not renew/hide Q. Q is reserved from E key configuration in the combined build. Q is on layer 100; E is on layer 90 with default `margin_y=110` to avoid the top direct-answer line.

The six E information-processing modules remain byte-identical to the E-only build. Only E's combined settings/default layout differ. Q never emits `reveal` to the probability tracker. Even after Q shows the true next shell, E remains 40%/60% with only public 2-live/3-blank counts, or 25%/75% after a lawful phone reveal of live position 3.

Multiplayer Q keeps its explicit local-active-player and `STEAM_ID == HOST_ID` checks. Ordinary clients cannot use it to obtain a chamber the host does not share. E uses local legitimate observations without changing network packets. Q is a cheat/direct-answer feature; do not describe the entire combined build as knowledge-only.

## Build

Python 3.11+; exact supported vanilla SHA256:

```text
df2f8a31bd469438a1a29f831945ccea7b26963ab735f73b32936792207b1663
```

```powershell
python -B .\CombinedVision\tools\build_variants.py `
  --source 'C:\Games\Buckshot Roulette\Buckshot Roulette.vanilla.exe' `
  --variant combined `
  --output '.\build\combined\Buckshot Roulette.QE.exe' `
  --report '.\build\combined\build-verification.json' `
  --runtime-dir '.\build\combined\ProbabilityVision'
```

Use `q` and `e` with distinct filenames/directories to retain independent outputs and backups. Inputs are read-only; output/report/runtime destinations must be new. The `q` build modifies 2 game scripts and adds no resources; `e` modifies 14 and adds 8; `combined` modifies 15 and adds 8. The shared singleplayer ShellSpawner is composed, not replaced wholesale by the old Q-only snippet.

Keep generated builds/reports locally. Reports can contain absolute filesystem paths; `.gitignore` excludes build outputs and receipts. Only the inspected game version is supported. Do not remove hash/anchor guards to apply to an updated game.

## Install / restore

Builds do not automatically modify the installation. Close the game before installing. From the repository root:

```powershell
.\CombinedVision\install.ps1 -GameDirectory 'C:\Games\Buckshot Roulette' -PackageDirectory '.\build\combined' -WhatIf
.\CombinedVision\install.ps1 -GameDirectory 'C:\Games\Buckshot Roulette' -PackageDirectory '.\build\combined'
```

Installation creates a uniquely named verified pre-install backup and a local receipt. Restore with:

```powershell
.\CombinedVision\restore.ps1 -Receipt 'path-to-local-QE-install-receipt.json' -WhatIf
.\CombinedVision\restore.ps1 -Receipt 'path-to-local-QE-install-receipt.json'
```

Restore retains both versions. If a target was subsequently updated or modified, scripts refuse to overwrite it. To switch variants, restore the recognized prior/vanilla backup first. For a manual Q-only install, close the game, keep a separate current EXE backup, and copy the generated Q-only executable into the original game directory as `Buckshot Roulette.exe`. Do not double-click these copied EXEs outside the original game/dependency directory.

Packed default configuration is sufficient. To customize E, copy the generated `ProbabilityVision/probability_vision.cfg` next to the game EXE. Existing configuration is not overwritten. User-selected overlapping positions can still overlap; keep y110 or another separate area for combined mode.

## Validation

The standalone E suite has 82 runtime assertions. `tests/run_isolation_tests.gd` contains 57 additional assertions that exercise the actual Q template alongside the E plugin: same public information with different true orders gives identical E snapshots, legal phone knowledge stays separate, keys/timers/widgets/scene cleanup are independent.

The isolation suite must run with the **combined runtime configuration** (Q reserved, y110), not the standalone E configuration at repository root. Export a separate test project from MOD source only, without any game files:

```powershell
python -B .\CombinedVision\tools\prepare_isolation_project.py --output '.\.build\isolation'
godot --headless --path '.\.build\isolation' --script res://CombinedVision/tests/run_isolation_tests.gd
python -B .\CombinedVision\tests\test_q_hooks.py
```

The combined native compile checker includes all 15 hooked game scripts and the E plugin, using inert autoloads so it does not initialize Steam. For gameplay regression testing, check private multiplayer with only the host modified, both sides modified, repeated items, lag, reloads, deaths and scene exits.

See [Probability Vision](../ProbabilityVision/README.md) for detailed legal event sources, posterior inference, unknown-inverter count uncertainty and test cases.
