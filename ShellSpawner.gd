
func _input(event):
	if Input.is_key_pressed(KEY_Q):
		var shellStr = ">"
		for shell in sequenceArray:
			if(shell == "live"): shellStr += "1"
			else: shellStr += "0"
		dialogue.ShowText_ForDuration(shellStr, 3)

