extends Node

const Tracker = preload("res://ProbabilityVision/GameStateTracker.gd")
const HUD = preload("res://ProbabilityVision/ProbabilityHUD.gd")
const Settings = preload("res://ProbabilityVision/Config.gd")
const NODE_NAME = "ProbabilityVision"
var tracker = Tracker.new()
var hud
var settings: Dictionary
var session_owner: WeakRef
var mode: String
var detaching: bool = false

static func attach(context: Node, session_mode: String) -> void:
	if not is_instance_valid(context) or context.get_tree() == null:
		return
	var root = context.get_tree().root
	var scene_owner = context
	while scene_owner.get_parent() != root and scene_owner.get_parent() != null:
		scene_owner = scene_owner.get_parent()
	var existing = root.get_node_or_null(NodePath(NODE_NAME))
	if is_instance_valid(existing):
		existing._detach()
	var instance = load("res://ProbabilityVision/ProbabilityVisionPlugin.gd").new()
	instance.name = NODE_NAME
	instance.mode = session_mode
	instance.session_owner = weakref(scene_owner)
	# A game node may attach while its scene is still propagating _ready.
	root.add_child.call_deferred(instance)
	scene_owner.tree_exiting.connect(instance._detach, CONNECT_ONE_SHOT)

static func emit_event(context: Node, event: String, payload: Dictionary) -> void:
	if not is_instance_valid(context) or context.get_tree() == null:
		return
	var instance = context.get_tree().root.get_node_or_null(NodePath(NODE_NAME))
	if is_instance_valid(instance):
		var owner = instance.session_owner.get_ref()
		if not is_instance_valid(owner) or instance.detaching:
			return
		if context != owner and not owner.is_ancestor_of(context):
			return
		if payload.has("generation") and payload.generation != instance.tracker.active_generation:
			return
		instance.tracker.handle_event(event, payload)
		if event == "reset":
			instance.hud.hide_hud()

static func generation(context: Node) -> int:
	if is_instance_valid(context) and context.get_tree() != null:
		var instance = context.get_tree().root.get_node_or_null(NodePath(NODE_NAME))
		if is_instance_valid(instance):
			return instance.tracker.active_generation
	return -1

func _ready() -> void:
	settings = Settings.read_settings()
	hud = HUD.new()
	add_child(hud)
	hud.setup(settings)
	tracker.changed.connect(hud.update_snapshot)
	hud.update_snapshot(tracker.snapshot())

func _input(event: InputEvent) -> void:
	# No set_input_as_handled: preserve original keyboard/game interaction.
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == OS.find_keycode_from_string(settings.toggle_key):
			hud.toggle()

func _detach() -> void:
	if detaching:
		return
	detaching = true
	if is_instance_valid(hud):
		hud.hide_hud()
	tracker.handle_event("reset", {})
	set_process_input(false)
	call_deferred("_finish_detach")

func _finish_detach() -> void:
	if get_parent() != null:
		get_parent().remove_child(self)
	queue_free()
