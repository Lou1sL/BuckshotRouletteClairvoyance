extends RefCounted

# Receives only already-disclosed information. No game nodes or shell arrays.
static func reveal(state, payload: Dictionary) -> void:
	if payload.get("source", "") not in ["phone", "magnifier"]:
		state.invalidate("Unapproved disclosure source")
		return
	if not payload.has("position") or not payload.has("live"):
		state.invalidate("Incomplete item disclosure")
		return
	if not payload.live is bool or not payload.position is int:
		state.invalidate("Invalid item disclosure")
		return
	state.observe(payload.position, payload.live)

static func invert(state) -> void:
	# Never read the shell produced by the inverter, or the new actual counts.
	state.invert_first()
