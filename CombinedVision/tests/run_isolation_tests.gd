extends SceneTree
## Runs the shipped SP Q template together with the shipped E plugin.
## No real game session, hidden game resource, Steam API or input injection.

const Plugin = preload("res://ProbabilityVision/ProbabilityVisionPlugin.gd")
const Settings = preload("res://ProbabilityVision/Config.gd")
const TEMPLATE_PATH = "res://CombinedVision/QSingleplayer.gdfrag"

var checks: int = 0
var failures: Array = []


func check(condition: bool, label: String) -> void:
	checks += 1
	if not condition:
		failures.append(label)
		printerr("FAIL: ", label)


func unchanged(before: Dictionary, plugin, label: String) -> void:
	check(plugin.tracker.snapshot() == before, label)
	check(plugin.tracker.snapshot().known_shells == {3: true}, label + " keeps only legal phone knowledge")
	check(is_equal_approx(plugin.tracker.snapshot().next_live_probability, 0.25), label + " keeps 25%")


func key_event(code: int, pressed: bool = true, echo: bool = false) -> InputEventKey:
	var event = InputEventKey.new()
	event.keycode = code
	event.pressed = pressed
	event.echo = echo
	return event


func finish() -> void:
	print("COMBINED_VISION_ISOLATION_TESTS ", JSON.stringify({
		"checks": checks,
		"failures": failures,
		"passed": failures.is_empty(),
	}))
	quit(0 if failures.is_empty() else 1)


func _initialize() -> void:
	call_deferred("run")


func run() -> void:
	check(Settings.sanitize_settings({"toggle_key": "Q"}).toggle_key == "E", "Q is reserved: E key config falls back")
	check(Settings.DEFAULTS.margin_y == 110, "E default offset leaves room for Q")
	var template = FileAccess.get_file_as_string(TEMPLATE_PATH)
	check(not template.is_empty(), "actual shipped Q template exists")
	if template.is_empty():
		finish()
		return
	var script = GDScript.new()
	script.source_code = "extends Node\nvar sequenceArray: Array = []\nfunc _process(delta):\n\t_RefreshDirectSequence()\n" + template
	var parsed: int = script.reload()
	check(parsed == OK, "actual Q template compiles in host fixture")
	if parsed != OK:
		finish()
		return
	var owner = Node.new()
	root.add_child(owner)
	var q = script.new()
	owner.add_child(q)
	# Explicit refresh calls make timing deterministic; no 3-second sleeps.
	q.set_process(false)
	Plugin.attach(owner, "singleplayer")
	await process_frame
	await process_frame
	var plugin = root.get_node_or_null("ProbabilityVision")
	check(is_instance_valid(plugin), "real E plugin attaches")
	if not is_instance_valid(plugin):
		owner.queue_free()
		finish()
		return
	Plugin.emit_event(owner, "load_public", {"live": 2, "blank": 3})
	check(is_equal_approx(plugin.tracker.snapshot().next_live_probability, 0.4), "E starts at public 40% despite Q fixture")
	q.sequenceArray = ["live", "blank", "live", "blank", "blank"]
	var no_phone = plugin.tracker.snapshot().duplicate(true)
	q._input(key_event(KEY_Q))
	check(is_instance_valid(q._direct_sequence_label), "Q creates its own label")
	check(q._direct_sequence_label.visible, "Q shows directly on key press")
	check("10100" in q._direct_sequence_label.text, "Q retains full direct order feature")
	check(plugin.tracker.snapshot() == no_phone, "Q true next live does not turn E 40% into 100%")
	check(plugin.tracker.snapshot().known_shells.is_empty(), "Q answer is not a legal Known event")
	check(not plugin.hud.panel.visible, "Q does not open E")
	check(q._direct_sequence_label.get_parent().layer == 100 and plugin.hud.layer == 90, "Q and E use distinct layers")
	check(q._direct_sequence_label.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Q overlay does not consume mouse input")
	check(q._direct_sequence_label != plugin.hud.body, "Q and E use distinct text widgets")

	Plugin.emit_event(owner, "reveal", {"position": 3, "live": true, "source": "phone"})
	var legal = plugin.tracker.snapshot().duplicate(true)
	unchanged(legal, plugin, "phone #3 gives legal baseline")
	q._RefreshDirectSequence()
	unchanged(legal, plugin, "Q refresh has no knowledge side effect")
	# Same public counts and same legally known #3, different hidden #1/#2.
	q.sequenceArray = ["blank", "live", "live", "blank", "blank"]
	q._RefreshDirectSequence()
	check("01100" in q._direct_sequence_label.text, "Q refresh follows its own hidden fixture")
	unchanged(legal, plugin, "changing hidden order leaves entire E snapshot identical")

	# Use a sentinel expiry, so a repeated show would be detectably different.
	q._direct_sequence_until_msec = Time.get_ticks_msec() + 9000
	var deadline: int = q._direct_sequence_until_msec
	var direct_text: String = q._direct_sequence_label.text
	q._input(key_event(KEY_Q, true, true))
	check(q._direct_sequence_until_msec == deadline, "Q key echo does not renew timer")
	q._input(key_event(KEY_Q, false))
	check(q._direct_sequence_until_msec == deadline, "Q key release does not show again")
	q._input(key_event(KEY_E))
	check(q._direct_sequence_until_msec == deadline, "pressing E while Q is visible does not retrigger Q")
	plugin._input(key_event(KEY_Q))
	check(not plugin.hud.panel.visible, "Q event does not toggle E HUD")
	plugin._input(key_event(KEY_E))
	check(plugin.hud.panel.visible and q._direct_sequence_label.visible, "Q and E can be visible together")
	check(q._direct_sequence_until_msec == deadline and q._direct_sequence_label.text == direct_text, "E show leaves Q text and deadline untouched")
	unchanged(legal, plugin, "E show leaves knowledge untouched")
	plugin._input(key_event(KEY_E, true, true))
	check(plugin.hud.panel.visible, "E key repeat is ignored")
	plugin._input(key_event(KEY_E))
	check(not plugin.hud.panel.visible and q._direct_sequence_label.visible, "E hide does not hide Q")
	check(q._direct_sequence_until_msec == deadline and q._direct_sequence_label.text == direct_text, "E hide leaves Q state untouched")
	unchanged(legal, plugin, "E hide leaves knowledge untouched")

	plugin._input(key_event(KEY_E))
	q._direct_sequence_until_msec = Time.get_ticks_msec() - 1
	q._RefreshDirectSequence()
	check(not q._direct_sequence_label.visible, "Q timeout hides only Q")
	check(plugin.hud.panel.visible, "Q timeout does not hide E")
	unchanged(legal, plugin, "Q timeout leaves knowledge untouched")
	q._input(key_event(KEY_Q))
	check(q._direct_sequence_label.visible, "fresh Q press shows again")
	unchanged(legal, plugin, "reopening Q leaves knowledge untouched")
	q.sequenceArray = []
	q._RefreshDirectSequence()
	check(not q._direct_sequence_label.visible, "empty Q chamber hides direct label")
	unchanged(legal, plugin, "Q empty/hide does not reset unrelated E model")
	q.sequenceArray = ["blank", "live", "live", "blank", "blank"]
	q._input(key_event(KEY_Q))
	deadline = q._direct_sequence_until_msec
	direct_text = q._direct_sequence_label.text
	Plugin.emit_event(owner, "reset", {})
	check(not plugin.hud.panel.visible and not plugin.tracker.snapshot().valid, "legal E reset clears model and hides E")
	check(q._direct_sequence_label.visible and q._direct_sequence_until_msec == deadline and q._direct_sequence_label.text == direct_text, "E reset does not mutate Q overlay")

	var direct_label = q._direct_sequence_label
	owner.queue_free()
	await process_frame
	await process_frame
	check(not is_instance_valid(q) and not is_instance_valid(direct_label), "owning scene exit destroys Q host and label")
	check(not is_instance_valid(root.get_node_or_null("ProbabilityVision")), "owning scene exit destroys E plugin and knowledge")
	finish()
