"""Build Q, E, or combined from the user's own exact vanilla executable.

Python 3.11+. All inputs are read-only. No previous modded EXE is needed.
The existing ProbabilityVision source provides E adapters and the PCK writer.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ProbabilityVision" / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build import RUNTIME_FILES, VANILLA_SHA256, prepare as prepare_e
from pck import read_pack, resource_bytes, sha256, write_pack
import q_hooks

CONFIG = "res://ProbabilityVision/Config.gd"
CFG = "res://ProbabilityVision/probability_vision.cfg"
EXPECTED_COUNTS = {"q": (2, 0), "e": (14, 8), "combined": (15, 8)}


def _replace_once(text, anchor, replacement, name):
    count = text.count(anchor)
    if count != 1:
        raise ValueError(f"{name}: anchor expected once, found {count}: {anchor!r}")
    return text.replace(anchor, replacement, 1)


def configure_combined_runtime(additions):
    """Return a new runtime dict with reserved Q and lower E HUD position.

    Six information-processing modules stay byte-for-byte unchanged. This is
    also usable when preparing an isolated test project containing no game.
    """
    expected_names = {"res://ProbabilityVision/" + name for name in RUNTIME_FILES}
    if set(additions) != expected_names:
        raise ValueError("Unexpected ProbabilityVision runtime module set")
    result = dict(additions)
    for name in (CONFIG, CFG):
        text = additions[name].decode("utf-8")
        newline = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("\r\n", "\n")
        if name == CONFIG:
            text = _replace_once(text, '\t"margin_y": 28,', '\t"margin_y": 110,', name)
            text = _replace_once(
                text, "\treturn settings\n",
                "\t# Q belongs to the independent direct display in this variant.\n"
                "\tif OS.find_keycode_from_string(settings.toggle_key) == KEY_Q:\n"
                '\t\tsettings["toggle_key"] = "E"\n'
                "\treturn settings\n", name,
            )
        else:
            text = _replace_once(text, "margin_y=28\n", "margin_y=110\n", name)
        result[name] = text.replace("\n", newline).encode("utf-8")
    for name in expected_names - {CONFIG, CFG}:
        if result[name] != additions[name]:
            raise ValueError(f"E information-processing module changed: {name}")
    return result


def prepare(source, variant):
    """Produce replacement/addition bytes without writing any output files."""
    source = Path(source)
    if variant not in EXPECTED_COUNTS:
        raise ValueError(f"Unknown variant: {variant!r}")
    if variant == "q":
        if sha256(source) != VANILLA_SHA256:
            raise ValueError("Unsupported EXE: use the inspected v2.2.0 hotfix 6 vanilla backup")
        replacements, additions = {}, {}
    else:
        # The existing E preparation validates the exact vanilla hash and all
        # original adapter anchors. Its game scripts and modules stay intact.
        replacements, additions = prepare_e(source)
    if variant in ("q", "combined"):
        pack = read_pack(source)
        for path in q_hooks.HOOK_PATHS:
            name = "res://" + path
            original = replacements.get(name)
            if original is None:
                original = resource_bytes(source, pack, name)
            replacements[name] = q_hooks.transform(path, original.decode("utf-8")).encode("utf-8")
    if variant == "combined":
        additions = configure_combined_runtime(additions)
    expected_replacements, expected_additions = EXPECTED_COUNTS[variant]
    if len(replacements) != expected_replacements or len(additions) != expected_additions:
        raise ValueError(f"Unexpected resource counts for {variant}: {len(replacements)}/{len(additions)}")
    return replacements, additions


def _validate_destinations(source, output, report, runtime_dir):
    paths = [source.resolve(), output.resolve(), report.resolve()]
    if len(set(paths)) != len(paths):
        raise ValueError("Source, output, and report must be distinct paths")
    if any(first in second.parents for first in paths for second in paths if first != second):
        raise ValueError("Source, output, and report must not contain one another")
    if output.exists() or report.exists():
        raise ValueError("Output/report already exist; refusing to overwrite them")
    if runtime_dir is not None:
        runtime = runtime_dir.resolve()
        if runtime_dir.exists():
            raise ValueError("Runtime directory already exists; use a new directory")
        for path in paths:
            if runtime == path or runtime in path.parents or path in runtime.parents:
                raise ValueError("Runtime directory must be separate from source/output/report")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--variant", choices=tuple(EXPECTED_COUNTS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, help="Optional new directory for the added E runtime modules")
    args = parser.parse_args()
    _validate_destinations(args.source, args.output, args.report, args.runtime_dir)
    if not args.source.is_file():
        raise ValueError("Source must be an existing local game executable")
    source_hash = sha256(args.source)
    replacements, additions = prepare(args.source, args.variant)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # The existing writer independently verifies all resources, the native
    # executable prefix, additions, and exact replacement payloads afterward.
    report = write_pack(args.source, args.output, replacements, additions)
    if sha256(args.source) != source_hash:
        raise ValueError("Source executable changed during build")
    if args.runtime_dir is not None:
        args.runtime_dir.mkdir(parents=True, exist_ok=False)
        for name, data in additions.items():
            target = args.runtime_dir / name.removeprefix("res://ProbabilityVision/")
            with target.open("xb") as stream:
                stream.write(data)
    report.update({
        "variant": args.variant,
        "game_version": "Steam v2.2.0 hotfix 6",
        "godot_version": "4.1.1",
        "source": str(args.source.resolve()),
        "output": str(args.output.resolve()),
        "output_bytes": args.output.stat().st_size,
        "q_display_included": args.variant != "e",
        "q_multiplayer_support": "host only" if args.variant != "e" else "not included",
        "e_multiplayer_support": "local public knowledge" if args.variant != "q" else "not included",
        "q_display_updates_probability_knowledge": False,
        "probability_logic_matches_e_only": args.variant != "q",
        "e_default_margin_y": 110 if args.variant == "combined" else (28 if args.variant == "e" else None),
        "q_reserved_key": args.variant == "combined",
        "live_game_test_performed": False,
    })
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
