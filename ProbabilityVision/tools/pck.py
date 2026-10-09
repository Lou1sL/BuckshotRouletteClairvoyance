"""Plain Godot 4.1.1 embedded-PCK reader/writer, streaming unchanged assets.

Resource offsets/header layout follow the upstream Godot PCK implementation.
No engine rebuild, Steam DLL replacement, encryption, or native-code hooks.
"""

import hashlib
import struct
from pathlib import Path

MAGIC = 0x43504447
CHUNK = 1024 * 1024


def exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("Truncated PCK")
    return data


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_pack(path):
    with Path(path).open("rb") as stream:
        stream.seek(0, 2)
        length = stream.tell()
        if length < 112:
            raise ValueError("Not an embedded PCK")
        stream.seek(length - 12)
        size, magic = struct.unpack("<QI", exact(stream, 12))
        start = length - 12 - size
        if magic != MAGIC or start < 0:
            raise ValueError("Invalid PCK footer")
        stream.seek(start)
        header = struct.unpack("<6IQ", exact(stream, 32))
        if header[:6] != (MAGIC, 2, 4, 1, 1, 0):
            raise ValueError(f"Unsupported PCK: {header}")
        base = header[6]
        reserved = exact(stream, 64)
        count = struct.unpack("<I", exact(stream, 4))[0]
        if not 0 < count < 100000:
            raise ValueError("Invalid directory size")
        entries = {}
        for _ in range(count):
            name_size = struct.unpack("<I", exact(stream, 4))[0]
            if not 0 < name_size < 65536:
                raise ValueError("Invalid path length")
            name = exact(stream, name_size).rstrip(b"\0").decode("utf-8")
            offset, payload_size, md5, flags = struct.unpack("<QQ16sI", exact(stream, 36))
            absolute = base + offset
            if name in entries or not name.startswith("res://") or "/../" in name:
                raise ValueError(f"Invalid or duplicate resource: {name}")
            if flags or absolute < base or absolute + payload_size > length - 12:
                raise ValueError(f"Unsupported resource: {name}")
            entries[name] = {"absolute": absolute, "size": payload_size, "md5": md5}
        if base < stream.tell():
            raise ValueError("Payload overlaps directory")
        return {"start": start, "base": base, "length": length, "reserved": reserved, "entries": entries}


def resource_bytes(path, pack, name):
    entry = pack["entries"][name]
    with Path(path).open("rb") as stream:
        stream.seek(entry["absolute"])
        data = exact(stream, entry["size"])
    if hashlib.md5(data).digest() != entry["md5"]:
        raise ValueError(f"Source MD5 invalid: {name}")
    return data


def digest_range(stream, start, size):
    stream.seek(start)
    md5, sha = hashlib.md5(), hashlib.sha256()
    while size:
        chunk = exact(stream, min(size, CHUNK))
        md5.update(chunk)
        sha.update(chunk)
        size -= len(chunk)
    return md5.digest(), sha.hexdigest()


def _copy_range(source, output, start, size):
    source.seek(start)
    md5 = hashlib.md5()
    while size:
        chunk = exact(source, min(size, CHUNK))
        md5.update(chunk)
        output.write(chunk)
        size -= len(chunk)
    return md5.digest()


def write_pack(source_path, output_path, replacements, additions):
    source_path, output_path = Path(source_path), Path(output_path)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("Refusing to modify source")
    pack = read_pack(source_path)
    original = pack["entries"]
    if not replacements.keys() <= original.keys() or additions.keys() & original.keys():
        raise ValueError("Invalid replacement/addition set")
    names = sorted(set(original) | set(additions))
    records = {}
    with source_path.open("rb") as source, output_path.open("xb") as output:
        _copy_range(source, output, 0, pack["start"])
        output.write(struct.pack("<6IQ", MAGIC, 2, 4, 1, 1, 0, 0))
        output.write(pack["reserved"])
        output.write(struct.pack("<I", len(names)))
        for name in names:
            encoded = name.encode("utf-8")
            encoded += b"\0" * (-len(encoded) % 4)
            output.write(struct.pack("<I", len(encoded)))
            output.write(encoded)
            records[name] = output.tell()
            output.write(bytes(36))
        output.write(bytes(-output.tell() % 16))
        file_base = output.tell()
        payload_records = {}
        for name in names:
            absolute = output.tell()
            data = replacements.get(name, additions.get(name))
            if data is not None:
                output.write(data)
                size = len(data)
                md5 = hashlib.md5(data).digest()
            else:
                entry = original[name]
                size = entry["size"]
                md5 = _copy_range(source, output, entry["absolute"], size)
                if md5 != entry["md5"]:
                    raise ValueError(f"Invalid source asset: {name}")
            payload_records[name] = (absolute - file_base, size, md5, 0)
            output.write(bytes(-output.tell() % 16))
        pack_size = output.tell() - pack["start"]
        output.write(struct.pack("<QI", pack_size, MAGIC))
        output.seek(pack["start"] + 24)
        output.write(struct.pack("<Q", file_base))
        for name, record in payload_records.items():
            output.seek(records[name])
            output.write(struct.pack("<QQ16sI", *record))
    return verify_pack(source_path, output_path, replacements, additions)


def verify_pack(source_path, output_path, replacements, additions):
    before, after = read_pack(source_path), read_pack(output_path)
    if before["start"] != after["start"]:
        raise ValueError("Engine prefix size changed")
    if set(after["entries"]) != set(before["entries"]) | set(additions):
        raise ValueError("Unexpected resource set")
    changed = []
    with Path(source_path).open("rb") as old, Path(output_path).open("rb") as new:
        if digest_range(old, 0, before["start"])[1] != digest_range(new, 0, after["start"])[1]:
            raise ValueError("Native executable bytes changed")
        for name, entry in before["entries"].items():
            target = after["entries"][name]
            old_md5, old_sha = digest_range(old, entry["absolute"], entry["size"])
            new_md5, new_sha = digest_range(new, target["absolute"], target["size"])
            if old_md5 != entry["md5"] or new_md5 != target["md5"]:
                raise ValueError(f"Resource checksum mismatch: {name}")
            if name in replacements:
                if new_sha != hashlib.sha256(replacements[name]).hexdigest():
                    raise ValueError(f"Replacement mismatch: {name}")
                changed.append(name)
            elif old_sha != new_sha:
                raise ValueError(f"Unrelated resource changed: {name}")
        for name, data in additions.items():
            target = after["entries"][name]
            md5, sha = digest_range(new, target["absolute"], target["size"])
            if md5 != target["md5"] or sha != hashlib.sha256(data).hexdigest():
                raise ValueError(f"Added resource mismatch: {name}")
    return {"source_sha256": sha256(source_path), "output_sha256": sha256(output_path),
            "engine_prefix_unchanged": True, "all_resource_md5_valid": True,
            "original_resource_count": len(before["entries"]),
            "output_resource_count": len(after["entries"]),
            "changed_resources": sorted(changed), "added_resources": sorted(additions),
            "unchanged_original_resources": len(before["entries"]) - len(replacements)}
