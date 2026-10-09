"""Inject observer hooks into the inspected Buckshot Roulette multiplayer scripts.

Only information shown to the local player enters Probability Vision.  In
particular, generic item packets contain a chamber type even for unrelated
items; those fields are deliberately not observed.  This module performs no
file access and never changes network packets or game rules.
"""

from __future__ import annotations


PREFIX = "multiplayer/scripts/"
HOOK_PATHS = (
    PREFIX + "global scripts/MP_GameStateManager.gd",
    PREFIX + "global scripts/MP_RoundManager.gd",
    PREFIX + "user scripts/MP_ShotgunInteraction.gd",
    PREFIX + "user scripts/MP_ItemInteraction.gd",
    PREFIX + "user scripts/MP_BurnerPhone.gd",
    PREFIX + "user scripts/MP_ShellEjection.gd",
)

BRIDGE = 'load("res://ProbabilityVision/ProbabilityVisionPlugin.gd")'


def _replace_once(text: str, anchor: str, replacement: str, path: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise ValueError(f"{path}: expected exactly one hook anchor, found {count}: {anchor!r}")
    return text.replace(anchor, replacement, 1)


def transform(path: str, text: str) -> str:
    """Return a source with exact, version-checked observer hooks inserted."""
    normalized_path = str(path).replace("\\", "/")
    if normalized_path.startswith("res://"):
        normalized_path = normalized_path[6:]
    if normalized_path not in HOOK_PATHS:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    result = text.replace("\r\n", "\n")
    if "# Probability Vision multiplayer observer" in result:
        raise ValueError(f"{path}: Probability Vision hooks are already present")

    def inject(anchor: str, replacement: str) -> None:
        nonlocal result
        result = _replace_once(result, anchor, replacement, normalized_path)

    if normalized_path.endswith("/MP_GameStateManager.gd"):
        inject(
            "func _ready():\n\tMAIN_active_running_intro = !skipping_intro",
            "func _ready():\n"
            "\t# Probability Vision multiplayer observer; this node lives for the match.\n"
            f'\t{BRIDGE}.attach(self, "multiplayer")\n'
            "\tMAIN_active_running_intro = !skipping_intro",
        )

    elif normalized_path.endswith("/MP_RoundManager.gd"):
        inject(
            '\t\t"first round routine":\n\t\t\tif !intro_finished:',
            '\t\t"first round routine":\n'
            '\t\t\t# Probability Vision multiplayer observer: discard the previous round.\n'
            f'\t\t\t{BRIDGE}.emit_event(self, "reset", {{}})\n'
            '\t\t\tif !intro_finished:',
        )
        inject(
            '\t\t"load shotgun routine":\n\t\t\tgame_state.FreeLookCameraForAllUsers_Disable()',
            '\t\t"load shotgun routine":\n'
            f'\t\t\t{BRIDGE}.emit_event(self, "reset", {{}})\n'
            '\t\t\tgame_state.FreeLookCameraForAllUsers_Disable()',
        )
        # Commit counts only after the machine has displayed the shells.  This
        # sequence is the public display, never the hidden shuffled chamber.
        inject(
            '\tawait get_tree().create_timer(game_state.MAIN_sequence_visible_duration, false).timeout\n'
            '\tspeaker_sequence_machine.stream = sound_hide',
            '\tawait get_tree().create_timer(game_state.MAIN_sequence_visible_duration, false).timeout\n'
            '\tvar pv_public_shells = game_state.MAIN_active_sequence_dict.get("sequence_visible", [])\n'
            f'\t{BRIDGE}.emit_event(self, "load_public", {{"live": pv_public_shells.count("live"), "blank": pv_public_shells.count("blank")}})\n'
            '\tspeaker_sequence_machine.stream = sound_hide',
        )
        inject(
            '\tif packet_dictionary.user_won_game_at_socket != -1:\n'
            '\t\tprint("user has won game. doing win shit & returning at mainroutine_userendturn")',
            '\tif packet_dictionary.user_won_game_at_socket != -1:\n'
            f'\t\t{BRIDGE}.emit_event(self, "reset", {{}})\n'
            '\t\tprint("user has won game. doing win shit & returning at mainroutine_userendturn")',
        )
        inject(
            'func GameConclusion(packet : Dictionary):\n\tgame_state.MAIN_active_match_result_statistics',
            'func GameConclusion(packet : Dictionary):\n'
            f'\t{BRIDGE}.emit_event(self, "reset", {{}})\n'
            '\tgame_state.MAIN_active_match_result_statistics',
        )

    elif normalized_path.endswith("/MP_ShotgunInteraction.gd"):
        inject(
            '\tRemoveFirstShellFromSequence()\n\t\n\tCheckIfFinalShot()',
            '\t# Probability Vision multiplayer observer: sound and shot outcome are now public.\n'
            f'\t{BRIDGE}.emit_event(self, "remove", {{"live": current_shell == "live", "source": "shot"}})\n'
            '\tRemoveFirstShellFromSequence()\n\t\n\tCheckIfFinalShot()',
        )

    elif normalized_path.endswith("/MP_ItemInteraction.gd"):
        inject(
            'func InteractWithItem_FirstPerson(packet : Dictionary):\n',
            'func InteractWithItem_FirstPerson(packet : Dictionary):\n'
            f'\tvar pv_observation_epoch = {BRIDGE}.generation(self)\n',
        )
        inject(
            'var debug_index = -1\nfunc _unhandled_input(event):',
            '# Probability Vision multiplayer observer: a beer becomes public when its shell appears.\n'
            'var probability_vision_beer_pending := false\n\n'
            'var debug_index = -1\nfunc _unhandled_input(event):',
        )
        inject(
            '\t\t5:\t#beer\n\t\t\tshotgun.RemoveFirstShellFromSequence()',
            '\t\t5:\t#beer\n'
            '\t\t\tprobability_vision_beer_pending = true\n'
            '\t\t\tshotgun.RemoveFirstShellFromSequence()',
        )
        # Waiting for the entire first-person animation is conservative: no
        # result is learned before the local player's inspection was visible.
        inject(
            '\tanimator_items_firstperson.play(animation_name)\n'
            '\tif active_item_has_secondary_interaction: return\n'
            '\tawait get_tree().create_timer(animator_items_firstperson.get_animation(animation_name).length, false).timeout\n'
            '\tmatch active_id:',
            '\tanimator_items_firstperson.play(animation_name)\n'
            '\tif active_item_has_secondary_interaction: return\n'
            '\tawait get_tree().create_timer(animator_items_firstperson.get_animation(animation_name).length, false).timeout\n'
            '\tif packet.item_id == 2 && properties.is_active && !properties.cpu_enabled:\n'
            f'\t\t{BRIDGE}.emit_event(self, "reveal", {{"position": 1, "live": packet.current_shell_in_chamber == "live", "source": "magnifier", "generation": pv_observation_epoch}})\n'
            '\tmatch active_id:',
        )
        # An inverter changes the hypothesis distribution without disclosing
        # its actual input or output shell, including when somebody else uses it.
        for perspective in ("first", "third"):
            inject(
                f'\tanimator_items_{perspective}person.play(animation_name)\n',
                f'\tanimator_items_{perspective}person.play(animation_name)\n'
                '\tif packet.item_id == 9:\n'
                f'\t\t{BRIDGE}.emit_event(self, "invert", {{}})\n',
            )

    elif normalized_path.endswith("/MP_BurnerPhone.gd"):
        inject(
            'func ShowBurnerPhoneDialogue():\n'
            '\tproperties.dialogue.ShowText_Forever(GetBurnerPhoneString(game_state.MAIN_phone_verbal_index, game_state.MAIN_phone_verbal_shell))',
            'func ShowBurnerPhoneDialogue():\n'
            '\tproperties.dialogue.ShowText_Forever(GetBurnerPhoneString(game_state.MAIN_phone_verbal_index, game_state.MAIN_phone_verbal_shell))\n'
            '\t# Probability Vision multiplayer observer: ignore host-held secrets belonging to others.\n'
            '\tif properties.is_active && !properties.cpu_enabled && properties.is_interacting_with_item && properties.item_interaction.active_id == 6:\n'
            '\t\tif game_state.MAIN_phone_verbal_index >= 1 && game_state.MAIN_phone_verbal_shell in ["live", "blank"]:\n'
            f'\t\t\t{BRIDGE}.emit_event(self, "reveal", {{"position": game_state.MAIN_phone_verbal_index, "live": game_state.MAIN_phone_verbal_shell == "live", "source": "phone"}})',
        )

    elif normalized_path.endswith("/MP_ShellEjection.gd"):
        inject(
            '\tshell_branch.SetState(shell_to_eject)\n'
            '\tanimator_fade_out.play("set visible")\n'
            '\tanimator_eject.play("eject shell")',
            '\tshell_branch.SetState(shell_to_eject)\n'
            '\tanimator_fade_out.play("set visible")\n'
            '\tanimator_eject.play("eject shell")\n'
            '\t# Probability Vision multiplayer observer: only beer; shot outcome already consumed its shell.\n'
            '\tif properties.item_interaction.probability_vision_beer_pending && properties.is_interacting_with_item && properties.item_interaction.active_id == 5:\n'
            '\t\tproperties.item_interaction.probability_vision_beer_pending = false\n'
            f'\t\t{BRIDGE}.emit_event(self, "remove", {{"live": shell_to_eject == "live", "source": "beer"}})',
        )

    return result.replace("\n", newline)
