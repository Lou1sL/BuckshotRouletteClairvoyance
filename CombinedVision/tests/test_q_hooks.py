"""Synthetic adapter tests; contain no complete original game scripts/assets."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import q_hooks
import build_variants


SP_SOURCE = "extends Node\n\nfunc _process(delta):\n\tpass\n\nfunc after_process():\n\tpass\n"
MP_SOURCE = (
    "extends Node\n\nfunc _process(delta):\n\tLerpBus()\n\n"
    "func _unhandled_input(event):\n"
    '\tif event.is_action_pressed("exit game") && is_active:\n'
    '\t\tintermediary.ingame_lobby_ui.ToggleUI()\n\n'
    'func later_game_method():\n\tpass\n'
)


class QHookTests(unittest.TestCase):
    def test_singleplayer_preserves_process_and_uses_strict_q(self):
        result = q_hooks.transform(q_hooks.SP, SP_SOURCE)
        self.assertIn("\t_RefreshDirectSequence()\n\tpass\n", result)
        self.assertIn("event.keycode == KEY_Q", result)
        self.assertIn("not event.echo", result)
        self.assertIn("func after_process():\n\tpass", result)
        self.assertNotIn(".emit_event", result)
        self.assertNotIn("dialogue.", result)

    def test_multiplayer_keeps_host_guard_and_original_methods(self):
        result = q_hooks.transform(q_hooks.MP, MP_SOURCE)
        self.assertIn("\tLerpBus()\n\t_RefreshClairvoyance()\n", result)
        self.assertIn("GlobalSteam.STEAM_ID != GlobalSteam.HOST_ID", result)
        self.assertIn("\telif event is InputEventKey:", result)
        self.assertIn("func later_game_method():\n\tpass", result)
        self.assertNotIn(".emit_event", result)

    def test_res_paths_and_crlf(self):
        for path, source in ((q_hooks.SP, SP_SOURCE), (q_hooks.MP, MP_SOURCE)):
            lf = q_hooks.transform(path, source)
            self.assertEqual(q_hooks.transform("res://" + path, source), lf)
            self.assertEqual(q_hooks.transform(path.replace("/", "\\"), source), lf)
            self.assertEqual(q_hooks.transform(path, source.replace("\n", "\r\n")), lf.replace("\n", "\r\n"))

    def test_unrelated_source_is_unchanged(self):
        source = "whatever\r\n"
        self.assertIs(q_hooks.transform("unrelated.gd", source), source)

    def test_missing_and_duplicate_anchors_are_rejected(self):
        for path, source in ((q_hooks.SP, SP_SOURCE), (q_hooks.MP, MP_SOURCE)):
            with self.assertRaises(ValueError):
                q_hooks.transform(path, "")
            with self.assertRaises(ValueError):
                q_hooks.transform(path, source + "\nfunc _process(delta):\n\tpass\n")
            with self.assertRaises(ValueError):
                q_hooks.transform(path, q_hooks.transform(path, source))
        with self.assertRaises(ValueError):
            q_hooks.transform(q_hooks.SP, SP_SOURCE.replace("\tpass\n", "\tpass\n\tpass\n", 1))
        with self.assertRaises(ValueError):
            q_hooks.transform(q_hooks.MP, MP_SOURCE.replace("\tLerpBus()\n", "\tLerpBus()\n\tLerpBus()\n", 1))

    def test_singleplayer_accepts_e_hooked_source(self):
        source = SP_SOURCE + '\nfunc e_observation():\n\tload("res://ProbabilityVision/ProbabilityVisionPlugin.gd").emit_event(self, "reset", {})\n'
        result = q_hooks.transform(q_hooks.SP, source)
        self.assertIn(source.split("func e_observation():", 1)[1], result)
        self.assertEqual(result.count('.emit_event(self, "reset", {})'), 1)


class CombinedRuntimeTests(unittest.TestCase):
    def runtime(self):
        source_root = PROJECT.parent / "ProbabilityVision"
        return {"res://ProbabilityVision/" + name: (source_root / name).read_bytes()
                for name in build_variants.RUNTIME_FILES}

    def test_only_two_settings_files_change(self):
        original = self.runtime()
        snapshot = dict(original)
        combined = build_variants.configure_combined_runtime(original)
        self.assertIsNot(original, combined)
        self.assertEqual(original, snapshot)
        changed = {name for name in combined if combined[name] != original[name]}
        self.assertEqual(changed, {build_variants.CONFIG, build_variants.CFG})
        config = combined[build_variants.CONFIG].decode("utf-8")
        self.assertIn('"margin_y": 110,', config)
        self.assertIn("OS.find_keycode_from_string(settings.toggle_key) == KEY_Q", config)
        self.assertIn("margin_y=110", combined[build_variants.CFG].decode("utf-8"))

    def test_configuration_rejects_unsupported_or_already_configured_runtime(self):
        runtime = self.runtime()
        with self.assertRaises(ValueError):
            build_variants.configure_combined_runtime({})
        with self.assertRaises(ValueError):
            build_variants.configure_combined_runtime(build_variants.configure_combined_runtime(runtime))

    def test_wrong_source_and_unknown_variant_are_rejected(self):
        for variant in build_variants.EXPECTED_COUNTS:
            with self.assertRaises(ValueError):
                build_variants.prepare(Path(__file__), variant)
        with self.assertRaises(ValueError):
            build_variants.prepare(Path(__file__), "invalid")

    def test_colliding_destinations_are_rejected_before_build(self):
        source, output, report = (Path(name) for name in ("source.exe", "output.exe", "report.json"))
        with patch.object(Path, "exists", return_value=False):
            for candidate in (
                (source, source, report, None),
                (source, output, output / "report.json", None),
                (source, output, report, output),
                (source, output, report, output.parent / "report.json" / "runtime"),
            ):
                with self.assertRaises(ValueError):
                    build_variants._validate_destinations(*candidate)

    def test_existing_output_report_or_runtime_are_rejected(self):
        existing = Path(__file__)
        source, output, report = (Path(name) for name in ("source.exe", "unused-output.exe", "unused-report.json"))
        for candidate in (
            (source, existing, report, None),
            (source, output, existing, None),
            (source, output, report, existing.parent),
        ):
            with self.assertRaises(ValueError):
                build_variants._validate_destinations(*candidate)


if __name__ == "__main__":
    unittest.main()
