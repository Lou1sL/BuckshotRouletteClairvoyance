extends SceneTree

const Plugin = preload("res://ProbabilityVision/ProbabilityVisionPlugin.gd")

func _initialize() -> void:
	call_deferred("render_demo")

func render_demo() -> void:
	root.size = Vector2i(1280, 720)
	var background = ColorRect.new()
	background.color = Color("141917")
	background.size = root.size
	root.add_child(background)
	var owner = Node.new()
	root.add_child(owner)
	var script = GDScript.new()
	script.source_code = "extends Node\nvar sequenceArray: Array = []\nfunc _process(delta):\n\t_RefreshDirectSequence()\n" + FileAccess.get_file_as_string("res://CombinedVision/QSingleplayer.gdfrag")
	if script.reload() != OK:
		quit(1)
		return
	var direct = script.new()
	owner.add_child(direct)
	direct.sequenceArray = ["live", "blank", "live", "blank", "blank"]
	Plugin.attach(owner, "singleplayer")
	await process_frame
	await process_frame
	Plugin.emit_event(owner, "load_public", {"live": 2, "blank": 3})
	Plugin.emit_event(owner, "reveal", {"position": 3, "live": true, "source": "phone"})
	root.get_node("ProbabilityVision").hud.toggle()
	direct._ShowDirectSequence()
	await process_frame
	await RenderingServer.frame_post_draw
	var result = root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://HUD-preview.png"))
	print("COMBINED_HUD_PREVIEW_RESULT ", result)
	quit(0 if result == OK else 1)
