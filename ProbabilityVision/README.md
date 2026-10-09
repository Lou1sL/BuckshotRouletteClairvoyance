# Probability Vision / 概率透视（E-only）

Press **E** to show/hide a HUD derived exclusively from the player's legitimate information. It starts hidden and hides again when resetting/reloading. No hidden chamber answer or Q direct-order feature is included in the E-only build.

## Compatibility and framework

Inspected target: **Steam v2.2.0 hotfix 6, GodotSteam 4.1.1**, confirmed from actual `GlobalVariables.gd`, the game executable, resource directory, class cache and animation call sites. This is not a claim of compatibility with the newest release or other distributions.

The game logic is GDScript, so this implementation patches GDScript resources while preserving the original native engine and Steam libraries. It does not assume that a Unity-oriented BepInEx installation or a differently versioned GDWeave loader is compatible. PCK layout follows the official Godot 4.1.1 [reader](https://github.com/godotengine/godot/blob/4.1.1-stable/core/io/file_access_pack.cpp) and [packer](https://github.com/godotengine/godot/blob/4.1.1-stable/core/io/pck_packer.cpp).

The build rejects anything except the inspected vanilla SHA256:

```text
df2f8a31bd469438a1a29f831945ccea7b26963ab735f73b32936792207b1663
```

Adapters cover singleplayer, Double or Nothing and multiplayer local knowledge. Multiplayer host-held secrets about other players do not become the local player's knowledge. No network protocol changes are made.

## Modules

```text
ProbabilityVision/
  ProbabilityVisionPlugin.gd    # E input, scene ownership, lifecycle
  GameStateTracker.gd           # event routing and chamber generations
  PlayerKnowledgeState.gd       # independent player information state
  ProbabilityCalculator.gd     # pure probability and certainty derivation
  ItemEventTracker.gd           # legal disclosure-source validation
  ProbabilityHUD.gd            # renders only safe snapshots
  Config.gd
  probability_vision.cfg
  install.ps1 / restore.ps1
  tools/                       # source hooks, PCK implementation, E-only builder
  tests/                       # model, input, lifecycle, source-hook and compiler tests
```

## Information boundary

```text
Legitimate game observations → tracker → player knowledge
                            → pure calculator → safe snapshot → HUD
```

The HUD has no game-node, hidden-array or network-packet reference. `KnownShells` contains directly disclosed positions; `DerivedShells` contains only positions that agree in every compatible hypothesis, displayed separately in yellow. Position 1 always means the current next shell.

For an unknown next position and exact counts:

```text
unknownLive      = remainingLive - knownLive
unknownPositions = remainingTotal - knownPositionCount
P(nextLive)      = unknownLive / unknownPositions
```

Examples:

- 2 live + 3 blank, no positional information: 40% live / 60% blank.
- The phone reveals position 3 is live: 1 live among 4 unknown positions, so 25% / 75%.
- Beer ejects a publicly visible blank: position 3 moves to position 2, and the next live chance is 1/3.
- Position 1 is directly known: 0% or 100% is legitimate.
- With 2 live + 2 blank and known live positions 2 and 3, positions 1 and 4 are necessarily blank and appear under Derived.

### Unknown inverter and uncertain counts

Displaying the true new live count after an unknown inversion would disclose the original hidden first shell. For example, starting with 2 live / 3 blank, a true post-inversion count of 1 live exposes an originally live first shell; 3 live exposes an originally blank first shell.

Therefore the inverter hook emits **no shell type**. The probability changes from 40% / 60% to 60% / 40%, while counts show possibilities and expectations:

```text
Remaining: 5
Live: 1 or 3 (possible), mean 2.2
Blank: 2 or 4 (possible), mean 2.8
Next live: 60.0%
Next blank: 40.0%
```

A known position 1 is flipped and exact counts are updated. Later public shot/ejection/magnifier observations condition the uncertainty correctly. Two successive inverters restore the prior distribution.

The state maintains weighted hypotheses generated from public counts, **not a copy of the actual game order**. Reveal filters hypotheses; inversion flips their first bit; public consumption filters and shifts, merging equivalent hypotheses. Hypotheses are not exposed to the HUD. Multiple revealed positions and exclusion deductions are supported.

The maximum modeled chamber is 16 shells. Unsupported sizes, contradictions, malformed payloads, out-of-range information and empty double-removal invalidate the model. It waits for the next public reload instead of reading the hidden chamber to repair itself.

## Inspected event hooks

All locations below come from actual target-version scripts. Anchors are checked exactly once and the builder refuses partial/already-patched sources. Original game statements remain in order.

| Mode and script | Event boundary | Information accepted |
|---|---|---|
| SP `ShellSpawner` | `_ready`, `MainShellRoutine` | attach/reset; displayed live/blank counts |
| SP `ShellEjectManager` | `EjectShell`, `BeerEjection_player/dealer`, `DeathEjection` | visible single-shell result; consume and shift |
| SP `ShellExamine` | `SetupShell`, after shell becomes visible | local magnifier position 1 |
| SP `BurnerPhone` | `SendDialogue`, after shown text | actual phone position/type, excluding the one-shell no-answer case |
| SP `ItemInteraction` | inverter branch in `InteractWith` | inversion only, no true type |
| SP `HandManager` | visible inverter pickup/action | Dealer's public inversion, not its private decision |
| SP `RoundManager` / `UserExit` | new batch, round, death, exit | invalidate old knowledge |
| MP `MP_GameStateManager` | `_ready` / scene exit | bind and destroy session |
| MP `MP_RoundManager` | round/load/result routines | reset; count only public `sequence_visible` |
| MP `MP_ShotgunInteraction` | `ShootingOutcome`, after public result | one public consumed shell |
| MP `MP_ItemInteraction` | first-person magnifier animation completion | local non-CPU player's reveal, with generation guard |
| MP `MP_ItemInteraction` | first/third-person inverter animation | public inversion, without type payload |
| MP `MP_BurnerPhone` | `ShowBurnerPhoneDialogue` | local currently interacting real player's actual displayed result |
| MP `MP_ShellEjection` | visible ejection | only marked beer; avoids double-counting a shot |

Generic multiplayer item packets may contain a hidden chamber field even for unrelated items. It is deliberately ignored. Private phone/magnifier results of the Dealer or other users are not collected.

Events update the model; it does not poll the real chamber each frame. Turn changes preserve same-chamber knowledge. Scene ownership, disposal and reload generations prevent old asynchronous observations from crossing into a new chamber.

The inspected item set has no random reordering item. The model's `unknown_reorder` assumes an explicitly verified **uniform** reshuffle, retaining count uncertainty while forgetting positions. Arbitrary third-party reordering is not automatically safe: an adapter must reset and pause when its transformation is unknown. Uninspected rule-changing MOD combinations are unsupported.

## Build, install and configure

From the repository root, use Python 3.11+ and your own vanilla game copy:

```powershell
python -B .\CombinedVision\tools\build_variants.py `
  --source 'C:\Games\Buckshot Roulette\Buckshot Roulette.vanilla.exe' `
  --variant e `
  --output '.\build\e\Buckshot Roulette.ProbabilityVision.exe' `
  --report '.\build\e\build-verification.json'
```

The original `ProbabilityVision/tools/build.py` is also available. Builds do not install themselves. They verify the engine prefix, every resource MD5, unchanged assets and complete output SHA256. E-only changes 14 game scripts and adds 8 runtime/config resources; 3558 original resources remain unchanged.

Close the game. Inspect the install action, then run it with your actual game directory and build directory:

```powershell
.\ProbabilityVision\install.ps1 -GameDirectory 'C:\Games\Buckshot Roulette' -PackageDirectory '.\build\e' -WhatIf
.\ProbabilityVision\install.ps1 -GameDirectory 'C:\Games\Buckshot Roulette' -PackageDirectory '.\build\e'
```

The script validates supported hashes, refuses a running/updated/unknown game, creates a unique verified pre-install backup and writes a local installation receipt. Existing external configuration is not overwritten. Restore with `ProbabilityVision/restore.ps1 -Receipt 'path-to-local-install-receipt.json'`. Restore retains the patched EXE and backup. Switching from an unrecognized modified variant should restore its own vanilla/pre-install backup first rather than bypass checks.

Copy `probability_vision.cfg` next to the game EXE to override packed defaults:

```ini
[hud]
language="zh"
decimals=1
toggle_key="E"
hud_position="top_left"
margin_x=28
margin_y=28
width=340
font_size=22
opacity=0.94
```

Languages: `zh/en`. Decimal places: 0–3. Position: `top_left/top_right/bottom_left/bottom_right`. Keys use Godot names, such as E or F8. Re-enter the gameplay scene to reload settings. Invalid types/settings fall back or clamp safely. The combined build reserves Q and changes the default vertical margin to 110; the E-only default above is unchanged.

## Validation and limitations

Standard Godot 4.1.1 runs the independent project without game files:

```powershell
godot --headless --path . --script res://ProbabilityVision/tests/run_tests.gd
```

There are 82 runtime assertions covering conditional examples, beer/shot shifting, known/unknown inversion, multiple observations, deductions, reload/reset, invalid inputs/configuration, display formats, E input and session disposal. Real-source adapter checks require the user's inspected vanilla EXE:

```powershell
python -B .\ProbabilityVision\tests\test_hooks.py --source 'path-to-your-supported-vanilla.exe'
```

For native GodotSteam compile validation, `tests/make_validation_pack.py` builds a local inert-autoload environment; `tests/check_game_scripts.gd` mounts the candidate and compiles 14 hooked scripts plus the plugin without initializing Steam or instantiating game nodes. Do not substitute `--check-only` and assume exit 0 proves integration: Godot 4.1.1 exits that path before registering game autoloads.

For gameplay regression testing in private games, check self/other live and blank shots, continuing turns, beer, magnifier, repeated phones, known/unknown inversion, other players' private reveals, deaths, new rounds, Double or Nothing, reconnect/restart and menu exit. Waiting/invalid HUD data must never be repaired from hidden order.

Report issues with version, mode, public action sequence and HUD screenshots. Do not post game executables, extracted original scripts, private packets, Steam identities or local installation receipts.
