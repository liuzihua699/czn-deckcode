"""Command-line entry point for offline deck-code conversion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def _load_sdk() -> SimpleNamespace:
    from czn_deckcode import Deck, decode, encode

    return SimpleNamespace(Deck=Deck, decode=decode, encode=encode)


def _read_text(path: str) -> str:
    if path != "-":
        return Path(path).read_text(encoding="utf-8-sig")
    binary = getattr(sys.stdin, "buffer", None)
    return (
        binary.read().decode("utf-8-sig")
        if binary is not None
        else sys.stdin.read().removeprefix("\ufeff")
    )


def _write_stream(stream: object, text: str) -> None:
    binary = getattr(stream, "buffer", None)
    if binary is not None:
        stream.flush()
        binary.write(text.encode("utf-8"))
        binary.flush()
    else:
        stream.write(text)


def _write_text(path: str | None, text: str) -> None:
    if path in (None, "-"):
        _write_stream(sys.stdout, text)
    else:
        with Path(path).open("w", encoding="utf-8", newline="\n") as output:
            output.write(text)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="czn-deckcode", description="CZN 离线卡组码编解码 SDK"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    encode = commands.add_parser("encode", help="将卡组 JSON 编码为卡组码")
    encode.add_argument("deck", metavar="DECK_JSON", help="UTF-8 JSON 文件，- 表示标准输入")
    encode.add_argument("-o", "--output", metavar="CODE_TXT", help="输出文件，默认标准输出")

    decode = commands.add_parser("decode", help="将卡组码解码为 JSON")
    decode.add_argument("code", metavar="CODE", help="卡组码，- 表示从标准输入读取")
    decode.add_argument("-o", "--output", metavar="DECK_JSON", help="输出文件，默认标准输出")

    return parser


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON 中不允许使用 {value}。")


def main(argv: list[str] | None = None) -> int:
    """Run a command and return its exit status, without exposing tracebacks."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)

    try:
        try:
            sdk = _load_sdk()
        except ImportError as error:
            raise RuntimeError("编解码模块暂未就绪。") from error

        if args.command == "encode":
            try:
                value = json.loads(_read_text(args.deck), parse_constant=_reject_json_constant)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"JSON 格式有误：第 {error.lineno} 行，第 {error.colno} 列。"
                ) from error
            deck = sdk.Deck.from_dict(value)
            _write_text(args.output, sdk.encode(deck) + "\n")
        else:
            code = (_read_text("-") if args.code == "-" else args.code).strip()
            if not code:
                raise ValueError("卡组码不能为空。")
            deck = sdk.decode(code)
            text = json.dumps(deck.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)
            _write_text(args.output, text + "\n")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        _write_stream(sys.stderr, f"错误：{error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
