"""Canonical ordering of class-level definitions.

Shared between the linter (``class-definitions-order`` check) and the formatter
(``gdformat --reorder-code``) so that code emitted by the formatter never trips
the linter's ordering rule.
"""
from .ast import Statement, Annotation
from .utils import find_name_token_among_children


DEFAULT_CLASS_DEFINITIONS_ORDER = [
    "tools",
    "classnames",
    "extends",
    "docstrings",
    "signals",
    "enums",
    "consts",
    "staticvars",
    "exports",
    "pubvars",
    "prvvars",
    "onreadypubvars",
    "onreadyprvvars",
    "others",
]


def is_statement_irrelevant(statement: Statement) -> bool:
    """Statements the ordering rule ignores: ``pass``, nested classes and
    non-``@tool`` standalone annotations (which decorate the next statement)."""
    if statement.kind == "pass_stmt":
        return True
    if statement.kind == "annotation":
        return Annotation(statement.lark_node).name != "tool"
    if statement.kind == "class_def":
        return True
    return False


# pylint: disable-next=too-many-return-statements, too-many-branches
def map_statement_to_section(statement: Statement) -> str:
    if statement.kind == "class_var_stmt":
        if any(
            annotation.name.startswith("export") for annotation in statement.annotations
        ):
            return "exports"
        if any(annotation.name == "onready" for annotation in statement.annotations):
            return "onready{}vars".format(
                _class_var_stmt_visibility(statement.lark_node)
            )
        return "{}vars".format(_class_var_stmt_visibility(statement.lark_node))
    if statement.kind == "signal_stmt":
        return "signals"
    if statement.kind == "extends_stmt":
        return "extends"
    if statement.kind == "classname_extends_stmt":
        return "extends"
    if statement.kind == "enum_stmt":
        return "enums"
    if statement.kind == "classname_stmt":
        return "classnames"
    if statement.kind == "const_stmt":
        return "consts"
    if (
        statement.kind == "annotation"
        and Annotation(statement.lark_node).name == "tool"
    ):
        return "tools"
    if statement.kind == "func_def":
        return "others"
    if statement.kind == "static_func_def":
        return "others"
    if statement.kind == "abstract_func_def":
        return "others"
    if statement.kind == "docstr_stmt":
        return "docstrings"
    if statement.kind == "static_class_var_stmt":
        return "staticvars"
    raise NotImplementedError


def _class_var_stmt_visibility(class_var_stmt) -> str:
    some_var_stmt = class_var_stmt.children[0]
    name_token = find_name_token_among_children(some_var_stmt)
    return "pub" if not name_token.value.startswith("_") else "prv"  # type: ignore
