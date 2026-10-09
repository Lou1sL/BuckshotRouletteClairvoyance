"""Build an offline native-engine compile fixture from the user's own game.

The fixture disables autoload callbacks without changing their declarations.
It is never installed and contains no scenes. Run with the game's GodotSteam
engine; a stock Godot engine lacks the native Steam singleton.
"""
import argparse
import hashlib
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pck import MAGIC, read_pack, resource_bytes
from build import VANILLA_SHA256
from pck import sha256


def inert_callbacks(data, names):
    text = data.decode("utf-8")
    for name in names:
        pattern = rf"(?m)^func {name}\([^\n]*\n(?:\t[^\n]*\n|[ \t]*\n)*"
        text, count = re.subn(pattern, f"func {name}():\n\tpass\n\n", text)
        if count != 1:
            raise ValueError(f"Expected exactly one callback: {name}")
    return text.encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checker", type=Path, default=Path(__file__).with_name("check_game_scripts.gd"))
    args = parser.parse_args()
    if sha256(args.source) != VANILLA_SHA256:
        raise ValueError("Unsupported vanilla source")
    pack = read_pack(args.source)
    project = '''config_version=5
[application]
config/name="Probability Vision Native Offline Check"
[autoload]
GlobalVariables="*res://pv_test_globals.gd"
GlobalSteam="*res://pv_test_steam.gd"
[rendering]
renderer/rendering_method="gl_compatibility"
'''
    resources = {
        "res://project.godot": project.encode(),
        "res://.godot/global_script_class_cache.cfg": resource_bytes(
            args.source, pack, "res://.godot/global_script_class_cache.cfg"),
        "res://pv_test_globals.gd": inert_callbacks(resource_bytes(
            args.source, pack, "res://scripts/GlobalVariables.gd"), ["_ready"]),
        "res://pv_test_steam.gd": inert_callbacks(resource_bytes(
            args.source, pack, "res://scripts/Steam.gd"), ["_ready", "_process", "InitializeSteam"]),
        "res://check_game_scripts.gd": args.checker.read_bytes(),
    }
    with args.output.open("xb") as stream:
        stream.write(struct.pack("<6IQ", MAGIC, 2, 4, 1, 1, 0, 0))
        stream.write(bytes(64))
        stream.write(struct.pack("<I", len(resources)))
        records = {}
        for name, data in resources.items():
            encoded = name.encode()
            encoded += bytes(-len(encoded) % 4)
            stream.write(struct.pack("<I", len(encoded)))
            stream.write(encoded)
            records[name] = stream.tell()
            stream.write(bytes(36))
        stream.write(bytes(-stream.tell() % 16))
        base = stream.tell()
        for name, data in resources.items():
            offset = stream.tell() - base
            stream.write(data)
            stream.write(bytes(-stream.tell() % 16))
            end = stream.tell()
            stream.seek(records[name])
            stream.write(struct.pack("<QQ16sI", offset, len(data), hashlib.md5(data).digest(), 0))
            stream.seek(end)
        size = stream.tell()
        stream.write(struct.pack("<QI", size, MAGIC))
        stream.seek(24)
        stream.write(struct.pack("<Q", base))
    print(f"Created inert offline fixture: {args.output}")


if __name__ == "__main__":
    main()
