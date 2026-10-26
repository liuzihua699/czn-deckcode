import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from czn_deckcode import cli
from czn_deckcode.models import Card, Deck


class CLITests(unittest.TestCase):
    def setUp(self):
        self.deck = Deck("30134", (Card("c_30134_srt1", god="神明"),))
        self.sdk = SimpleNamespace(
            Deck=Deck, encode=Mock(return_value="test-code"),
            decode=Mock(return_value=self.deck),
        )

    def invoke(self, args, stdin=""):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(cli, "_load_sdk", return_value=self.sdk),
            patch.object(cli.sys, "stdin", io.StringIO(stdin)),
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr),
        ):
            status = cli.main(args)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_encode_reads_stdin_and_writes_stdout(self):
        status, stdout, stderr = self.invoke(
            ["encode", "-"], json.dumps(self.deck.to_dict(), ensure_ascii=False)
        )
        self.assertEqual(status, 0)
        self.assertEqual(stdout, "test-code\n")
        self.assertEqual(stderr, "")
        self.sdk.encode.assert_called_once_with(self.deck)

    def test_utf8_stdin_works_even_when_text_stream_uses_other_encoding(self):
        value = json.dumps(self.deck.to_dict(), ensure_ascii=False).encode("utf-8-sig")
        source = io.TextIOWrapper(io.BytesIO(value), encoding="ascii")
        target = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        with (
            patch.object(cli, "_load_sdk", return_value=self.sdk),
            patch.object(cli.sys, "stdin", source),
            patch.object(cli.sys, "stdout", target),
        ):
            status = cli.main(["encode", "-"])
        self.assertEqual(status, 0)
        self.assertEqual(target.buffer.getvalue(), b"test-code\n")

    def test_stdin_with_bom_also_supports_text_only_streams(self):
        status, stdout, stderr = self.invoke(
            ["encode", "-"], "\ufeff" + json.dumps(self.deck.to_dict())
        )
        self.assertEqual((status, stdout, stderr), (0, "test-code\n", ""))

    def test_decode_reads_stdin_and_prints_pretty_unicode_json(self):
        status, stdout, stderr = self.invoke(["decode", "-"], "  test-code\n")
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), self.deck.to_dict())
        self.assertIn('\n  "charId": "30134",', stdout)
        self.assertIn("神明", stdout)
        self.assertTrue(stdout.endswith("\n"))
        self.sdk.decode.assert_called_once_with("test-code")

    def test_encode_reads_utf8_json_file_and_writes_code_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "构筑.json"
            output = Path(directory) / "卡组码.txt"
            source.write_text(json.dumps(self.deck.to_dict(), ensure_ascii=False), encoding="utf-8")
            status, stdout, stderr = self.invoke(["encode", str(source), "-o", str(output)])
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            self.assertEqual(output.read_bytes(), b"test-code\n")

    def test_decode_writes_utf8_json_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "构筑.json"
            status, stdout, stderr = self.invoke(["decode", "test-code", "-o", str(output)])
            self.assertEqual((status, stdout, stderr), (0, "", ""))
            text = output.read_text(encoding="utf-8")
            self.assertIn("神明", text)
            self.assertEqual(json.loads(text), self.deck.to_dict())

    def test_explicit_dash_output_uses_stdout(self):
        status, stdout, stderr = self.invoke(["decode", "test-code", "-o", "-"])
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), self.deck.to_dict())

    def test_invalid_input_returns_two_on_stderr_without_traceback(self):
        cases = [
            (["encode", "-"], "{broken"),
            (["encode", "-"], '{"charId":1,"cards":[]}'),
            (["encode", "-"], '{"charId":NaN,"cards":[]}'),
            (["decode", "-"], "  \n"),
        ]
        for args, stdin in cases:
            with self.subTest(args=args, stdin=stdin):
                status, stdout, stderr = self.invoke(args, stdin)
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn("错误：", stderr)
                self.assertNotIn("Traceback", stderr)

    def test_file_errors_return_two(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            status, stdout, stderr = self.invoke(["encode", str(missing)])
            self.assertEqual(status, 2)
            self.assertEqual(stdout, "")
            self.assertIn("错误：", stderr)
            status, stdout, stderr = self.invoke(["decode", "test-code", "-o", str(missing / "out.json")])
            self.assertEqual(status, 2)
            self.assertIn("错误：", stderr)

    def test_sdk_error_is_not_a_traceback(self):
        self.sdk.decode.side_effect = ValueError("无效卡组码")
        status, stdout, stderr = self.invoke(["decode", "broken"])
        self.assertEqual((status, stdout), (2, ""))
        self.assertEqual(stderr, "错误：无效卡组码\n")

    def test_missing_sdk_is_reported(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch.object(cli, "_load_sdk", side_effect=ImportError("not ready")),
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr),
        ):
            status = cli.main(["decode", "test-code"])
        self.assertEqual(status, 2)
        self.assertEqual(stderr.getvalue(), "错误：编解码模块暂未就绪。\n")

    def test_parser_errors_return_status_and_help_returns_zero(self):
        status, stdout, stderr = self.invoke([])
        self.assertEqual(status, 2)
        self.assertIn("usage:", stderr)
        self.assertEqual(stdout, "")
        status, stdout, stderr = self.invoke(["--help"])
        self.assertEqual(status, 0)
        self.assertIn("encode", stdout)
        self.assertEqual(stderr, "")

    def test_sdk_cli_does_not_offer_or_launch_the_separate_demo(self):
        for command in ("ui", "gui"):
            with self.subTest(command=command):
                status, stdout, stderr = self.invoke([command])
                self.assertEqual((status, stdout), (2, ""))
                self.assertIn("invalid choice", stderr)
        self.sdk.encode.assert_not_called()
        self.sdk.decode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
