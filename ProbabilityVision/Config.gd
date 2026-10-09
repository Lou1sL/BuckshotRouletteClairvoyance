extends RefCounted

const DEFAULTS = {
	"language": "zh",
	"decimals": 1,
	"toggle_key": "E",
	"hud_position": "top_left",
	"margin_x": 28,
	"margin_y": 28,
	"width": 340,
	"font_size": 22,
	"opacity": 0.94,
}

static func read_settings() -> Dictionary:
	var settings = DEFAULTS.duplicate(true)
	var cfg = ConfigFile.new()
	# An external config next to the executable overrides the packed defaults.
	var external = OS.get_executable_path().get_base_dir().path_join("probability_vision.cfg")
	var result = cfg.load(external)
	if result != OK:
		result = cfg.load("res://ProbabilityVision/probability_vision.cfg")
	if result == OK:
		for key in DEFAULTS:
			settings[key] = cfg.get_value("hud", key, DEFAULTS[key])
	return sanitize_settings(settings)

static func _integer(value, fallback: int) -> int:
	if value is int:
		return value
	if value is float and is_finite(value):
		return int(value)
	return fallback

static func _number(value, fallback: float) -> float:
	if value is int or value is float:
		var number = float(value)
		return number if is_finite(number) else fallback
	return fallback

static func sanitize_settings(values: Dictionary) -> Dictionary:
	# A syntactically valid config can still contain arrays/objects in numeric
	# fields. Validate types before conversion so a bad config cannot break HUD.
	var settings = DEFAULTS.duplicate(true)
	for key in DEFAULTS:
		settings[key] = values.get(key, DEFAULTS[key])
	settings["language"] = "en" if str(settings.language).to_lower() == "en" else "zh"
	settings["decimals"] = clampi(_integer(settings.decimals, DEFAULTS.decimals), 0, 3)
	settings["toggle_key"] = str(settings.toggle_key).to_upper()
	if OS.find_keycode_from_string(settings.toggle_key) == 0:
		settings["toggle_key"] = "E"
	if settings.hud_position not in ["top_left", "top_right", "bottom_left", "bottom_right"]:
		settings["hud_position"] = "top_left"
	settings["margin_x"] = clampi(_integer(settings.margin_x, DEFAULTS.margin_x), 0, 400)
	settings["margin_y"] = clampi(_integer(settings.margin_y, DEFAULTS.margin_y), 0, 400)
	settings["width"] = clampi(_integer(settings.width, DEFAULTS.width), 260, 640)
	settings["font_size"] = clampi(_integer(settings.font_size, DEFAULTS.font_size), 14, 36)
	settings["opacity"] = clampf(_number(settings.opacity, DEFAULTS.opacity), 0.3, 1.0)
	return settings
