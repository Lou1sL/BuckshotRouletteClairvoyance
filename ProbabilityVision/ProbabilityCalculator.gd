extends RefCounted
## Pure probability projection. Inputs contain player-compatible hypotheses only.
## Bit 0 is the NEXT shell; a set bit means live. UI receives no masks.


static func unavailable(reason: String) -> Dictionary:
	return {
		"valid": false,
		"reason": reason,
		"total_remaining": 0,
		"live_count_values": [],
		"blank_count_values": [],
		"live_expected": null,
		"blank_expected": null,
		"next_live_probability": null,
		"next_blank_probability": null,
		"known_shells": {},
		"derived_shells": {},
		"hypothesis_count": 0,
	}


static func count_live(mask: int, total: int) -> int:
	var count: int = 0
	for position in range(total):
		if (mask & (1 << position)) != 0:
			count += 1
	return count


static func calculate(hypotheses: Dictionary, total: int, known: Dictionary) -> Dictionary:
	if hypotheses.is_empty() or total < 0:
		return unavailable("empty_hypothesis_set")
	var weight_sum: float = 0.0
	var next_live_weight: float = 0.0
	var live_expectation_sum: float = 0.0
	var counts: Dictionary = {}
	var always_live: int = (1 << total) - 1
	var ever_live: int = 0
	for candidate in hypotheses:
		var mask: int = int(candidate)
		var weight: float = float(hypotheses[candidate])
		if weight <= 0.0 or not is_finite(weight):
			return unavailable("invalid_hypothesis_weight")
		var live_count: int = count_live(mask, total)
		counts[live_count] = true
		weight_sum += weight
		live_expectation_sum += weight * live_count
		if total > 0 and (mask & 1) != 0:
			next_live_weight += weight
		always_live &= mask
		ever_live |= mask
	if weight_sum <= 0.0 or not is_finite(weight_sum):
		return unavailable("invalid_total_weight")
	var live_values: Array = counts.keys()
	live_values.sort()
	var blank_values: Array = []
	for live_count in live_values:
		blank_values.append(total - int(live_count))
	blank_values.sort()
	var derived: Dictionary = {}
	for offset in range(total):
		var position: int = offset + 1
		if known.has(position):
			continue
		var bit: int = 1 << offset
		if (always_live & bit) != 0:
			derived[position] = true
		elif (ever_live & bit) == 0:
			derived[position] = false
	var next_live = null
	var next_blank = null
	if total > 0:
		next_live = next_live_weight / weight_sum
		next_blank = 1.0 - next_live
	return {
		"valid": true,
		"reason": "empty" if total == 0 else "",
		"total_remaining": total,
		"live_count_values": live_values,
		"blank_count_values": blank_values,
		"live_expected": live_expectation_sum / weight_sum,
		"blank_expected": total - live_expectation_sum / weight_sum,
		"next_live_probability": next_live,
		"next_blank_probability": next_blank,
		"known_shells": known.duplicate(true),
		"derived_shells": derived,
		"hypothesis_count": hypotheses.size(),
	}
