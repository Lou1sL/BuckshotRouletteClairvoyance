extends RefCounted

signal changed(snapshot)

const Knowledge = preload("res://ProbabilityVision/PlayerKnowledgeState.gd")
const Items = preload("res://ProbabilityVision/ItemEventTracker.gd")
var knowledge = Knowledge.new()
var active_generation: int = 0

func handle_event(event: String, payload: Dictionary) -> void:
	match event:
		"reset":
			active_generation += 1
			knowledge.invalidate("Waiting for a public reload")
		"load_public":
			if not payload.get("live") is int or not payload.get("blank") is int:
				knowledge.invalidate("Invalid public shell counts")
			else:
				knowledge.begin_load(payload.live, payload.blank)
		"reveal":
			Items.reveal(knowledge, payload)
		"remove":
			if not payload.get("live") is bool:
				knowledge.invalidate("Missing public ejection result")
			else:
				knowledge.remove_first(payload.live)
		"invert":
			Items.invert(knowledge)
		"unknown_reorder":
			# Randomize only the player model, retaining public count uncertainty.
			knowledge.unknown_reorder()
		_:
			knowledge.invalidate("Unsupported knowledge event")
	changed.emit(knowledge.snapshot())

func snapshot() -> Dictionary:
	return knowledge.snapshot()
