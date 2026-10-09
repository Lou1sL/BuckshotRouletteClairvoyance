"""Inject original Q display fragments into locally supplied game scripts.

No full game script or game executable is distributed with these adapters.
Both variants use isolated labels and never send observations to the E model.
"""

from pathlib import Path
import re

SP = "scripts/ShellSpawner.gd"
MP = "multiplayer/scripts/user scripts/MP_UserInstanceProperties.gd"
HOOK_PATHS = (SP, MP)
FRAGMENT_DIR = Path(__file__).resolve().parent.parent


def _function_bounds(path, text, function):
    matches = list(re.finditer(rf"(?m)^func {re.escape(function)}\([^\n]*\)[^\n]*:\n", text))
    if len(matches) != 1:
        raise ValueError(f"{path}: function {function!r} expected once, found {len(matches)}")
    start = matches[0].start()
    following = re.search(r"(?m)^func ", text[matches[0].end():])
    end = matches[0].end() + following.start() if following else len(text)
    return start, end


def _replace_in_function(path, text, function, needle, replacement):
    start, end = _function_bounds(path, text, function)
    scope = text[start:end]
    count = scope.count(needle)
    if count != 1:
        raise ValueError(f"{path}:{function}: anchor expected once, found {count}: {needle!r}")
    return text[:start] + scope.replace(needle, replacement, 1) + text[end:]


def _fragment(name):
    text = (FRAGMENT_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n")
    if ".emit_event" in text or 'res://ProbabilityVision/' in text or "dialogue." in text:
        raise ValueError(f"{name}: Q display must not depend on E knowledge or game dialogue")
    return text


def transform(path, text):
    """Return Q-patched text; fail on stale anchors or duplicate injection.

    SP accepts either the clean original or the existing E-hooked script.
    Paths may use res:// or Windows separators. Original line endings survive.
    """
    normalized_path = str(path).replace("\\", "/").removeprefix("res://")
    if normalized_path not in HOOK_PATHS:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    patched = text.replace("\r\n", "\n")
    if normalized_path == SP:
        if "func _input(" in patched or "_RefreshDirectSequence" in patched or "_direct_sequence_label" in patched:
            raise ValueError(f"{path}: existing SP input/Q display is unsupported")
        patched = _replace_in_function(
            normalized_path, patched, "_process", "\tpass\n",
            "\t_RefreshDirectSequence()\n\tpass\n",
        )
        fragment = _fragment("QSingleplayer.gdfrag")
        expected_functions = ("_input", "_ShowDirectSequence", "_RefreshDirectSequence")
    else:
        if "_ClairvoyanceSequence" in patched or "_clairvoyance_label" in patched:
            raise ValueError(f"{path}: multiplayer Q hooks are already present")
        patched = _replace_in_function(
            normalized_path, patched, "_process", "\tLerpBus()\n",
            "\tLerpBus()\n\t_RefreshClairvoyance()\n",
        )
        patched = _replace_in_function(
            normalized_path, patched, "_unhandled_input",
            "\t\tintermediary.ingame_lobby_ui.ToggleUI()\n",
            "\t\tintermediary.ingame_lobby_ui.ToggleUI()\n"
            "\telif event is InputEventKey:\n"
            "\t\tif event.pressed && !event.echo && event.keycode == KEY_Q:\n"
            "\t\t\t_ShowClairvoyance()\n",
        )
        fragment = _fragment("QMultiplayer.gdfrag")
        expected_functions = ("_ClairvoyanceSequence", "_ShowClairvoyance", "_RefreshClairvoyance")
    for function in expected_functions:
        _function_bounds(str(FRAGMENT_DIR), fragment, function)
    patched += "\n" + fragment.rstrip("\n") + "\n"
    return patched.replace("\n", newline)
