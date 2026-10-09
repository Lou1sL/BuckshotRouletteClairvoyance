"""Read-only adapter tests against the user's inspected original executable."""

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import singleplayer_hooks as sp
import multiplayer_hooks as mp
from pck import read_pack, resource_bytes, sha256
from build import VANILLA_SHA256

SOURCE = None


class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sha256(SOURCE) != VANILLA_SHA256:
            raise ValueError("Fixture must be the supported vanilla EXE")
        pack = read_pack(SOURCE)
        cls.sources = {path: resource_bytes(SOURCE, pack, "res://" + path).decode("utf-8")
                       for path in sp.HOOK_PATHS + mp.HOOK_PATHS}

    def test_all_14_scripts_insert_only_observers(self):
        for path, original in self.sources.items():
            with self.subTest(path=path):
                adapter = sp if path.startswith("scripts/") else mp
                patched = adapter.transform(path, original)
                self.assertNotEqual(patched, original)
                # Every original line remains in the same order. No game or AI
                # statement is replaced, omitted, reordered or intercepted.
                iterator = iter(patched.splitlines())
                for line in original.splitlines():
                    self.assertTrue(any(candidate == line for candidate in iterator), line)

    def test_already_patched_sources_fail(self):
        for path, original in self.sources.items():
            adapter = sp if path.startswith("scripts/") else mp
            with self.assertRaises(ValueError):
                adapter.transform(path, adapter.transform(path, original))

    def test_missing_function_or_anchor_fails(self):
        for path, original in self.sources.items():
            adapter = sp if path.startswith("scripts/") else mp
            with self.assertRaises(ValueError):
                adapter.transform(path, "extends Node\n")

    def test_unrelated_source_untouched(self):
        for adapter in (sp, mp):
            self.assertEqual(adapter.transform("scripts/DealerIntelligence.gd", "abc"), "abc")

    def test_CRLF_preserved(self):
        for path, original in self.sources.items():
            adapter = sp if path.startswith("scripts/") else mp
            windows = original.replace("\r\n", "\n").replace("\n", "\r\n")
            patched = adapter.transform(path, windows)
            self.assertNotIn("\n", patched.replace("\r\n", ""))

    def test_MP_secrets_not_collected_at_packet_receipt(self):
        path = "multiplayer/scripts/user scripts/MP_ItemInteraction.gd"
        patched = mp.transform(path, self.sources[path])
        start = patched.index("func ReceivePacket_InteractWithItem(")
        end = patched.index("func ReceivePacket_InteractWithItem_Secondary(")
        self.assertNotIn(".emit_event", patched[start:end])
        self.assertNotIn("sequence_in_shotgun", "\n".join(
            line for line in patched.splitlines() if ".emit_event" in line))
        self.assertIn("properties.is_active && !properties.cpu_enabled", patched)
        self.assertIn('"generation": pv_observation_epoch', patched)

    def test_inverter_has_no_result_payload(self):
        for path, original in self.sources.items():
            adapter = sp if path.startswith("scripts/") else mp
            patched = adapter.transform(path, original)
            for line in patched.splitlines():
                if '.emit_event(self, "invert"' in line:
                    self.assertTrue(line.rstrip().endswith('"invert", {})'))

    def test_hud_and_model_have_no_game_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ("ProbabilityHUD.gd", "PlayerKnowledgeState.gd", "ProbabilityCalculator.gd"):
            text = (root / filename).read_text(encoding="utf-8")
            for forbidden in ("sequenceArray", "sequence_in_shotgun", "MAIN_active_sequence_dict", "GlobalSteam"):
                self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    SOURCE = args.source
    unittest.main(argv=[sys.argv[0]], verbosity=2)
