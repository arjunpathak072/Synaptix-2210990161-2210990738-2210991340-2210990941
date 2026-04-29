"""Tree-sitter based symbol extraction for Python files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
_parser = Parser(PY_LANGUAGE)

# Node types we care about
_SYMBOL_TYPES = {"function_definition", "class_definition"}


@dataclass
class Symbol:
    name: str
    kind: str  # "function", "class", "method"
    start_line: int  # 0-indexed
    end_line: int  # 0-indexed
    parent_class: str | None = None


def extract_symbols(source: bytes) -> list[Symbol]:
    """Extract top-level functions, classes, and their methods from Python source."""
    tree = _parser.parse(source)
    symbols: list[Symbol] = []

    for node in tree.root_node.children:
        if node.type == "function_definition":
            name = node.child_by_field_name("name")
            if name:
                symbols.append(Symbol(
                    name=name.text.decode(),
                    kind="function",
                    start_line=node.start_point.row,
                    end_line=node.end_point.row,
                ))

        elif node.type == "class_definition":
            cls_name_node = node.child_by_field_name("name")
            if not cls_name_node:
                continue
            cls_name = cls_name_node.text.decode()
            symbols.append(Symbol(
                name=cls_name,
                kind="class",
                start_line=node.start_point.row,
                end_line=node.end_point.row,
            ))
            # Extract methods
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        mname = child.child_by_field_name("name")
                        if mname:
                            symbols.append(Symbol(
                                name=mname.text.decode(),
                                kind="method",
                                start_line=child.start_point.row,
                                end_line=child.end_point.row,
                                parent_class=cls_name,
                            ))

    return symbols


def extract_symbols_from_file(path: Path) -> list[Symbol]:
    """Extract symbols from a Python file on disk."""
    try:
        source = path.read_bytes()
    except (FileNotFoundError, PermissionError):
        return []
    return extract_symbols(source)


def get_symbol_chunk(path: Path, symbol: Symbol) -> str:
    """Read the exact source lines for a symbol."""
    try:
        lines = path.read_text().splitlines()
    except (FileNotFoundError, UnicodeDecodeError):
        return ""
    return "\n".join(lines[symbol.start_line : symbol.end_line + 1])
