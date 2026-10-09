"""Build against a user's own, exact inspected vanilla executable. Python 3.11+."""

import argparse
import json
from pathlib import Path

import multiplayer_hooks
import singleplayer_hooks
from pck import read_pack, resource_bytes, sha256, write_pack

VANILLA_SHA256 = "df2f8a31bd469438a1a29f831945ccea7b26963ab735f73b32936792207b1663"
RUNTIME_FILES = ("ProbabilityVisionPlugin.gd", "GameStateTracker.gd", "PlayerKnowledgeState.gd",
                 "ProbabilityCalculator.gd", "ItemEventTracker.gd", "ProbabilityHUD.gd", "Config.gd",
                 "probability_vision.cfg")


def prepare(source, inspection_dir=None):
    if sha256(source) != VANILLA_SHA256:
        raise ValueError("Unsupported EXE: use the inspected v2.2.0 hotfix 6 vanilla backup, not the Q-cheat EXE")
    pack = read_pack(source)
    paths = singleplayer_hooks.HOOK_PATHS + multiplayer_hooks.HOOK_PATHS
    replacements = {}
    for path in paths:
        name = "res://" + path
        text = resource_bytes(source, pack, name).decode("utf-8")
        transform = singleplayer_hooks.transform if path.startswith("scripts/") else multiplayer_hooks.transform
        patched = transform(path, text)
        if patched == text:
            raise ValueError(f"Required hooks missing: {path}")
        replacements[name] = patched.encode("utf-8")
        if inspection_dir:
            target = inspection_dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(replacements[name])
    root = Path(__file__).resolve().parent.parent
    additions = {"res://ProbabilityVision/" + name: (root / name).read_bytes() for name in RUNTIME_FILES}
    return replacements, additions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--inspection-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    paths = [args.source.resolve(), args.output.resolve(), args.report.resolve()]
    if len(set(paths)) != 3:
        raise ValueError("Source, output and report must be distinct")
    if args.output.exists() or args.report.exists():
        raise ValueError("Output/report already exist: refuse overwrite")
    if args.inspection_dir and (args.inspection_dir.exists() or args.inspection_dir.resolve() == args.source.parent.resolve()):
        raise ValueError("Inspection directory must be new and separate from game files")
    source_hash = sha256(args.source)
    replacements, additions = prepare(args.source, args.inspection_dir)
    if args.dry_run:
        print(json.dumps({"validated_hooks": list(replacements), "new_modules": list(additions)}, indent=2))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = write_pack(args.source, args.output, replacements, additions)
    if sha256(args.source) != source_hash:
        raise ValueError("Source changed during build")
    report.update({"game_version": "Steam v2.2.0 hotfix 6", "godot_version": "4.1.1",
                   "source": str(args.source.resolve()), "output": str(args.output.resolve()),
                   "output_bytes": args.output.stat().st_size, "hidden_Q_cheat_included": False,
                   "live_game_test_performed": False})
    with args.report.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
