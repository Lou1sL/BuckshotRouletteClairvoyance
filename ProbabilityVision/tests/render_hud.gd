extends SceneTree

const HUD = preload("res://ProbabilityVision/ProbabilityHUD.gd")
const State = preload("res://ProbabilityVision/PlayerKnowledgeState.gd")
const Config = preload("res://ProbabilityVision/Config.gd")

func _initialize() -> void:
	call_deferred("render_demo")

func render_demo() -> void:
	root.size = Vector2i(1280, 720)
	var background = ColorRect.new()
	background.color = Color("141917")
	background.size = root.size
	root.add_child(background)
	var config = Config.read_settings()
	var left = HUD.new()
	root.add_child(left)
	left.setup(config)
	var state = State.new()
	state.begin_load(2, 3)
	state.observe(3, true)
	left.update_snapshot(state.snapshot())
	left.toggle()
	config.hud_position = "top_right"
	var right = HUD.new()
	root.add_child(right)
	right.setup(config)
	state.begin_load(2, 3)
	state.invert_first()
	right.update_snapshot(state.snapshot())
	right.toggle()
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	var image = root.get_texture().get_image()
	var output = ProjectSettings.globalize_path("res://HUD-preview.png")
	var result = image.save_png(output)
	print("HUD_PREVIEW_RESULT ", result)
	quit(0 if result == OK else 1)
