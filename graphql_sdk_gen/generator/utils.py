from ast import AST, ImportFrom, alias, unparse

import isort
from black import Mode, format_str


def ast_to_str(ast_obj: AST) -> str:
    """Convert ast object into string."""
    return format_str(isort.code(unparse(ast_obj)), mode=Mode())


def generate_import_from(modules: list[str], from_: str, level: int = 0) -> ImportFrom:
    """Generate import from statement."""
    names = [alias(m) for m in modules]
    return ImportFrom(module=from_, names=names, level=level)
