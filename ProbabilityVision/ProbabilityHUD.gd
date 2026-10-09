extends CanvasLayer

const LIVE = "#ed6267"
const BLANK = "#c7d8df"
const DIM = "#929d96"
const DERIVED = "#dec875"
var settings: Dictionary
var panel: PanelContainer
var body: RichTextLabel
var latest: Dictionary = {"valid": false, "reason": "Waiting for public reload"}

func setup(config: Dictionary) -> void:
	settings = config.duplicate(true)
	layer = 90
	panel = PanelContainer.new()
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.custom_minimum_size.x = settings.width
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.055, 0.067, 0.061, settings.opacity)
	style.border_color = Color(0.35, 0.39, 0.34, 0.85)
	style.set_border_width_all(2)
	style.content_margin_left = 18
	style.content_margin_right = 18
	style.content_margin_top = 14
	style.content_margin_bottom = 14
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)
	body = RichTextLabel.new()
	body.bbcode_enabled = true
	body.fit_content = true
	body.scroll_active = false
	body.mouse_filter = Control.MOUSE_FILTER_IGNORE
	body.custom_minimum_size.x = settings.width - 40
	body.add_theme_font_size_override("normal_font_size", settings.font_size)
	body.add_theme_color_override("default_color", Color(0.83, 0.86, 0.8))
	panel.add_child(body)
	get_viewport().size_changed.connect(_layout)
	panel.resized.connect(_layout)
	_layout()
	hide_hud()

func _layout() -> void:
	if not is_instance_valid(panel):
		return
	var viewport_size = get_viewport().get_visible_rect().size
	var scale_factor = minf(1.0, maxf(0.1, viewport_size.y - settings.margin_y * 2.0) / maxf(1.0, panel.size.y))
	panel.scale = Vector2.ONE * scale_factor
	var shown_size = panel.size * scale_factor
	var pos = Vector2(settings.margin_x, settings.margin_y)
	if "right" in settings.hud_position:
		pos.x = maxf(0, viewport_size.x - shown_size.x - settings.margin_x)
	if "bottom" in settings.hud_position:
		pos.y = maxf(0, viewport_size.y - shown_size.y - settings.margin_y)
	panel.position = pos

func update_snapshot(value: Dictionary) -> void:
	latest = value.duplicate(true)
	if is_instance_valid(body):
		body.text = render_text(latest, settings)

func toggle() -> void:
	panel.visible = not panel.visible
	if panel.visible:
		body.text = render_text(latest, settings)

func hide_hud() -> void:
	if is_instance_valid(panel):
		panel.hide()

static func _percentage(value: float, decimals: int) -> String:
	return ("%.*f" % [decimals, value * 100.0]) + "%"

static func _counts(values: Array, expected: float, zh: bool, decimals: int) -> String:
	if values.size() == 1:
		return str(values[0])
	var pieces = PackedStringArray()
	for value in values:
		pieces.append(str(value))
	var expected_text = "%.*f" % [decimals, expected]
	return (" 或 " if zh else " or ").join(pieces) + ("（可能）\n  期望 " if zh else " (possible)\n  mean ") + expected_text

static func _positions(shells: Dictionary, color: String, zh: bool) -> String:
	if shells.is_empty():
		return "[color=" + DIM + "]" + ("无" if zh else "None") + "[/color]\n"
	var result = ""
	var positions = shells.keys()
	positions.sort()
	for position in positions:
		var kind = ("实弹" if shells[position] else "空包弹") if zh else ("LIVE" if shells[position] else "BLANK")
		result += "[color=" + color + "]" + (("第%d发 " % position) if zh else ("#%d " % position)) + kind + "[/color]\n"
	return result

static func render_text(snapshot: Dictionary, config: Dictionary) -> String:
	var zh = config.language == "zh"
	var decimals = int(config.decimals)
	var text = "[center]" + ("[ 概率分析 ]" if zh else "[ PROBABILITY VISION ]") + "[/center]\n[color=" + DIM + "]────────────────[/color]\n"
	if not snapshot.get("valid", false):
		return text + "[color=" + DIM + "]" + ("等待公开装弹信息\n信息未同步时暂停推算" if zh else "Waiting for public reload\nAnalysis paused until synchronized") + "[/color]"
	text += ("剩余弹药：" if zh else "REMAINING: ") + str(snapshot.total_remaining) + "\n"
	text += "[color=" + LIVE + "]" + ("实弹：" if zh else "LIVE: ") + _counts(snapshot.live_count_values, snapshot.live_expected, zh, decimals) + "[/color]\n"
	text += "[color=" + BLANK + "]" + ("空包：" if zh else "BLANK: ") + _counts(snapshot.blank_count_values, snapshot.blank_expected, zh, decimals) + "[/color]\n\n"
	if snapshot.total_remaining > 0:
		text += ("当前下一发\n" if zh else "NEXT\n")
		text += "[color=" + LIVE + "]" + ("实弹 " if zh else "LIVE  ") + _percentage(snapshot.next_live_probability, decimals) + "[/color]\n"
		text += "[color=" + BLANK + "]" + ("空包 " if zh else "BLANK ") + _percentage(snapshot.next_blank_probability, decimals) + "[/color]\n\n"
	else:
		text += ("弹仓已空\n\n" if zh else "CHAMBER EMPTY\n\n")
	text += ("已知信息\n" if zh else "KNOWN\n") + _positions(snapshot.known_shells, BLANK, zh)
	text += "\n" + ("推导信息\n" if zh else "DERIVED\n") + _positions(snapshot.derived_shells, DERIVED, zh)
	text += "\n[color=" + DIM + "]" + ("仅根据已公开信息 • " if zh else "Public knowledge only • ") + str(config.toggle_key) + (" 隐藏" if zh else " hide") + "[/color]"
	return text
