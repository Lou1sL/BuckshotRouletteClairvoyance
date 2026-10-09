"""Observer-only hooks for the verified Buckshot Roulette 4.1.1 scripts.

The builder supplies clean original source. No hook reads the hidden sequence
except one shell that the game is displaying as an actual public observation.
Dealer magnifier/phone knowledge and dealer decision-making are not observed.
"""

import re
from typing import NamedTuple


BRIDGE_PATH = "res://ProbabilityVision/ProbabilityVisionPlugin.gd"
BRIDGE = f'load("{BRIDGE_PATH}")'


class Anchor(NamedTuple):
    function: str
    needle: str
    replacement: str


def _emit(event: str, payload: str = "{}", indent: str = "\t") -> str:
    return f'{indent}{BRIDGE}.emit_event(self, "{event}", {payload})\n'


def _after(function: str, needle: str, code: str) -> Anchor:
    return Anchor(function, needle, needle + code)


def _before(function: str, needle: str, code: str) -> Anchor:
    return Anchor(function, needle, code + needle)


ANCHORS: dict[str, tuple[Anchor, ...]] = {
    "scripts/ShellSpawner.gd": (
        _before("_ready", "\tpass\n", f'\t{BRIDGE}.attach(self, "singleplayer")\n'),
        _after("MainShellRoutine", "func MainShellRoutine():\n", _emit("reset")),
        # All shells/audio indicators have been shown, including in DON where
        # textual shell descriptions are skipped. Use only the public counts.
        _before(
            "MainShellRoutine",
            "\tif(!roundManager.playerData.skippingShellDescription): await get_tree().create_timer(2.5, false).timeout\n",
            _emit("load_public", '{"live": temp_live, "blank": temp_blank}'),
        ),
    ),
    "scripts/ShellEjectManager.gd": tuple(
        _before(
            function,
            "\tshellSpawner.sequenceArray.remove_at(0)\n",
            _emit(
                "remove",
                '{"live": shellSpawner.sequenceArray[0] == "live", '
                f'"source": "{source}"' + "}",
            ),
        )
        for function, source in (
            ("EjectShell", "shot"),
            ("BeerEjection_player", "beer"),
            ("BeerEjection_dealer", "beer"),
            ("DeathEjection", "shot"),
        )
    ),
    "scripts/ShellExamine.gd": (
        # The compiled main scene's SetupShell method track belongs to the
        # player magnifier animation, not the dealer magnifier animation.
        _after(
            "SetupShell",
            "\tshellParent.visible = true\n",
            _emit("reveal", '{"position": 1, "live": shellState == "live", "source": "magnifier"}'),
        ),
    ),
    "scripts/BurnerPhone.gd": (
        _after(
            "SendDialogue",
            "\tdia.ShowText_Forever(fulldia)\n",
            "\tif len != 1:\n"
            + _emit(
                "reveal",
                '{"position": randindex + 1, "live": sequence[randindex] == "live", "source": "phone"}',
                "\t\t",
            ),
        ),
    ),
    "scripts/ItemInteraction.gd": (
        _after(
            "InteractWith",
            '\t\t\telse: roundManager.shellSpawner.sequenceArray[0] = "live"\n',
            _emit("invert", "{}", "\t\t\t"),
        ),
    ),
    "scripts/HandManager.gd": (
        # The dealer changes its internal shell before taking the item from
        # the table. Observe only the later visible/audible inverter action.
        _after(
            "PickupItemFromTable",
            "\tanimator_hands.play(animationName)\n",
            '\tif itemName == "inverter":\n' + _emit("invert", "{}", "\t\t"),
        ),
    ),
    "scripts/RoundManager.gd": (
        _after("MainBatchSetup", "func MainBatchSetup(dealerEnterAtStart : bool):\n", _emit("reset")),
        _after("StartRound", "func StartRound(gettingNext : bool):\n", _emit("reset")),
        _after("OutOfHealth", "func OutOfHealth(who : String):\n", _emit("reset")),
    ),
    "scripts/UserExit.gd": (
        _after("ExitGame", "func ExitGame():\n", _emit("reset")),
    ),
}

HOOK_PATHS = tuple(ANCHORS)


def _function_bounds(path: str, text: str, function: str) -> tuple[int, int]:
    pattern = rf"(?m)^func {re.escape(function)}\([^\n]*\)[^\n]*:\n"
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"{path}: function {function!r} expected once, found {len(matches)}")
    start = matches[0].start()
    following = re.search(r"(?m)^func ", text[matches[0].end():])
    end = matches[0].end() + following.start() if following else len(text)
    return start, end


def transform(path: str, text: str) -> str:
    """Return patched source, or unchanged text for an unsupported path.

    Every needle must occur exactly once within its named original function.
    An incompatible or already patched supported script fails before returning
    any transformed text, so the caller cannot silently deploy a partial hook.
    LF and CRLF input are supported; the original newline style is retained.
    """
    normalized_path = path.replace("\\", "/")
    supported = [
        candidate
        for candidate in HOOK_PATHS
        if normalized_path == candidate or normalized_path.endswith("/" + candidate)
    ]
    if not supported:
        return text
    if len(supported) != 1:
        raise ValueError(f"{path}: ambiguous hook path")
    hook_path = supported[0]
    if BRIDGE_PATH in text:
        raise ValueError(f"{hook_path}: Probability Vision hooks already present")
    newline = "\r\n" if "\r\n" in text else "\n"
    patched = text.replace("\r\n", "\n")
    for anchor in ANCHORS[hook_path]:
        start, end = _function_bounds(hook_path, patched, anchor.function)
        scope = patched[start:end]
        count = scope.count(anchor.needle)
        if count != 1:
            raise ValueError(
                f"{hook_path}:{anchor.function}: anchor expected once, found {count}: {anchor.needle!r}"
            )
        patched = patched[:start] + scope.replace(anchor.needle, anchor.replacement, 1) + patched[end:]
    return patched.replace("\n", newline)
