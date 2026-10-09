extends SceneTree

# Run inside a minimal validation PCK with inert autoloads, NOT --check-only.
# This mounts the candidate after the globals exist. It loads script resources
# but never instantiates game nodes, enters a match, or initializes Steam.
const PATHS = [
	"res://scripts/ShellSpawner.gd",
	"res://scripts/ShellEjectManager.gd",
	"res://scripts/ShellExamine.gd",
	"res://scripts/BurnerPhone.gd",
	"res://scripts/ItemInteraction.gd",
	"res://scripts/HandManager.gd",
	"res://scripts/RoundManager.gd",
	"res://scripts/UserExit.gd",
	"res://multiplayer/scripts/global scripts/MP_GameStateManager.gd",
	"res://multiplayer/scripts/global scripts/MP_RoundManager.gd",
	"res://multiplayer/scripts/user scripts/MP_ShotgunInteraction.gd",
	"res://multiplayer/scripts/user scripts/MP_ItemInteraction.gd",
	"res://multiplayer/scripts/user scripts/MP_BurnerPhone.gd",
	"res://multiplayer/scripts/user scripts/MP_ShellEjection.gd",
	"res://ProbabilityVision/ProbabilityVisionPlugin.gd",
]

func _initialize() -> void:
	var args = OS.get_cmdline_user_args()
	if args.size() != 1 or not ProjectSettings.load_resource_pack(args[0], true):
		printerr("Expected one candidate EXE path after --")
		quit(1)
		return
	var failures = []
	for path in PATHS:
		var script = load(path)
		if script == null or not script.can_instantiate():
			failures.append(path)
	print("PROBABILITY_VISION_NATIVE_CHECK ", JSON.stringify({
		"scripts_checked": PATHS.size(), "failures": failures,
		"passed": failures.is_empty(), "game_nodes_instantiated": false,
		"steam_initialized": false,
	}))
	quit(0 if failures.is_empty() else 1)
