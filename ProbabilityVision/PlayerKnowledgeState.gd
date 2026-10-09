extends RefCounted
## Independent player-knowledge model. Never receives a real chamber array.
## Events MUST be gated by the adapter: public load counts, observed results,
## and item information actually delivered to the local player only.

const Calculator = preload("res://ProbabilityVision/ProbabilityCalculator.gd")
const MAX_TRACKED_SHELLS: int = 16

var _valid: bool = false
var _reason: String = "awaiting_public_load"
var _total: int = 0
# Candidate masks -> unnormalised positive probability mass. Initial candidates
# are equally weighted. Reordering may produce unequal weights across counts.
var _hypotheses: Dictionary = {}
var _known: Dictionary = {}


func begin_load(live: int, blank: int) -> bool:
	if live < 0 or blank < 0 or live + blank > MAX_TRACKED_SHELLS:
		invalidate("invalid_public_load_counts")
		return false
	_total = live + blank
	_known.clear()
	_hypotheses.clear()
	_append_combinations(0, _total, live, 0, 1.0, _hypotheses)
	_valid = true
	_reason = ""
	return true


func observe(position: int, live: bool) -> bool:
	if not _valid:
		return false
	if position < 1 or position > _total:
		invalidate("observed_position_out_of_range")
		return false
	var bit: int = 1 << (position - 1)
	var filtered: Dictionary = {}
	for candidate in _hypotheses:
		if (((int(candidate) & bit) != 0) == live):
			filtered[candidate] = _hypotheses[candidate]
	if filtered.is_empty():
		invalidate("contradictory_public_observation")
		return false
	_hypotheses = filtered
	_known[position] = live
	_normalise_weights()
	return true


func remove_first(observed_live: bool) -> bool:
	if not _valid:
		return false
	if _total < 1:
		invalidate("removal_from_empty_chamber")
		return false
	# A shot or beer ejection exposes its result. Condition BEFORE shifting.
	var remaining: Dictionary = {}
	for candidate in _hypotheses:
		var mask: int = int(candidate)
		if (((mask & 1) != 0) == observed_live):
			var shifted: int = mask >> 1
			remaining[shifted] = float(remaining.get(shifted, 0.0)) + float(_hypotheses[candidate])
	if remaining.is_empty():
		invalidate("contradictory_public_removal")
		return false
	_hypotheses = remaining
	var shifted_known: Dictionary = {}
	for position in _known:
		if int(position) > 1:
			shifted_known[int(position) - 1] = _known[position]
	_known = shifted_known
	_total -= 1
	_normalise_weights()
	return true


func invert_first() -> bool:
	if not _valid:
		return false
	if _total < 1:
		invalidate("inversion_of_empty_chamber")
		return false
	var inverted: Dictionary = {}
	for candidate in _hypotheses:
		inverted[int(candidate) ^ 1] = _hypotheses[candidate]
	_hypotheses = inverted
	if _known.has(1):
		_known[1] = not bool(_known[1])
	# Do NOT fetch new real counts here: unknown inversion makes totals unknown.
	return true


func unknown_reorder() -> bool:
	if not _valid:
		return false
	var count_weights: Dictionary = {}
	for candidate in _hypotheses:
		var live_count: int = Calculator.count_live(int(candidate), _total)
		count_weights[live_count] = float(count_weights.get(live_count, 0.0)) + float(_hypotheses[candidate])
	var reordered: Dictionary = {}
	for live_count in count_weights:
		var candidates: Dictionary = {}
		_append_combinations(0, _total, int(live_count), 0, 1.0, candidates)
		var weight: float = float(count_weights[live_count]) / candidates.size()
		for candidate in candidates:
			reordered[candidate] = weight
	_hypotheses = reordered
	_known.clear()
	_normalise_weights()
	return true


func invalidate(reason: String) -> void:
	_valid = false
	_reason = reason
	_total = 0
	_hypotheses.clear()
	_known.clear()


func snapshot() -> Dictionary:
	if not _valid:
		return Calculator.unavailable(_reason)
	return Calculator.calculate(_hypotheses, _total, _known)


func _normalise_weights() -> void:
	var sum: float = 0.0
	for candidate in _hypotheses:
		sum += float(_hypotheses[candidate])
	if sum <= 0.0 or not is_finite(sum):
		invalidate("invalid_probability_mass")
		return
	for candidate in _hypotheses:
		_hypotheses[candidate] = float(_hypotheses[candidate]) / sum


func _append_combinations(offset: int, total: int, live_needed: int, mask: int, weight: float, result: Dictionary) -> void:
	if live_needed < 0 or live_needed > total - offset:
		return
	if offset == total:
		result[mask] = weight
		return
	_append_combinations(offset + 1, total, live_needed, mask, weight, result)
	_append_combinations(offset + 1, total, live_needed - 1, mask | (1 << offset), weight, result)
