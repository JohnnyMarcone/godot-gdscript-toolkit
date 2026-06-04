import pytest

from gdtoolkit.formatter import format_code, check_formatting_safety
from gdtoolkit.linter import lint_code


MAX_LINE_LENGTH = 100


def _reorder(code, spaces_for_indent=None):
    return format_code(
        code,
        max_line_length=MAX_LINE_LENGTH,
        spaces_for_indent=spaces_for_indent,
        reorder_code=True,
    )


# Exact input -> output pairs pinning the canonical ordering.
# fmt: off
EXACT_CASES = [
    (
        "var x\nsignal s\n",
        "signal s\nvar x\n",
    ),
    (
        "var x = 1\nconst C = 1\nextends Node\n@tool\n",
        "@tool\nextends Node\nconst C = 1\nvar x = 1\n",
    ),
    (
        "static func foo():\n\tpass\nstatic var sv = 1\nenum E { A, B }\n",
        "enum E { A, B }\n\nstatic var sv = 1\n\n\nstatic func foo():\n\tpass\n",
    ),
    # comments and inline comments travel with their member
    (
        "# foo doc\nfunc foo():\n\tpass\nsignal s  # the signal\n",
        "signal s  # the signal\n\n\n# foo doc\nfunc foo():\n\tpass\n",
    ),
    # @export / @onready stay attached; private sorts after public
    (
        "var pub\nvar _prv\n@onready var o = 1\n@export var e = 2\n",
        "@export var e = 2\nvar pub\nvar _prv\n@onready var o = 1\n",
    ),
]
# fmt: on


@pytest.mark.parametrize("code,expected", EXACT_CASES)
def test_reorder_exact_output(code, expected):
    formatted = _reorder(code)
    assert formatted == expected
    check_formatting_safety(code, formatted, MAX_LINE_LENGTH, reorder_code=True)


# Broader inputs (including every linter class-definitions-order failure case,
# nested classes and property bodies) checked for the invariants that matter:
# the result is lint-clean, idempotent, and passes the safety checks.
# fmt: off
INVARIANT_CASES = [
    "var x\nsignal s\n",
    "extends Node;var x\nsignal s\n",
    "class X:\n\tvar x\n\textends Node\n",
    "var _x\nvar x\n",
    "@onready var x\nvar y\n",
    "@onready var _x\n@onready var x\n",
    "var x\nenum X { A, B }\n",
    "var x\nclass_name Asdf\n",
    "var x\nconst X = 1\n",
    "var x\n@tool\n",
    "static func foo(): pass\nvar x\n",
    "'docstring'\nextends Node\n",
    # nested class is reordered internally and sorts among functions/classes
    "class Inner:\n\tfunc m():\n\t\tpass\n\tvar a = 1\n\tsignal inner_sig\n"
    "var top = 1\nsignal top_sig\n",
    # a property body must stay glued to its var when the var moves
    "func foo():\n\tpass\nvar prop:\n\tget:\n\t\treturn prop\n"
    "\tset(value):\n\t\tprop = value\nsignal s\n",
    # comments must be preserved across reordering
    "# leading\nfunc foo():\n\tpass\n\n# sig comment\nsignal s  # inline\nvar x = 1\n",
]
# fmt: on


@pytest.mark.parametrize("code", INVARIANT_CASES)
def test_reorder_is_lint_clean_idempotent_and_safe(code):
    formatted = _reorder(code)
    # safety checks (order-insensitive tree invariant, stability, comments)
    check_formatting_safety(code, formatted, MAX_LINE_LENGTH, reorder_code=True)
    # reordering its own output changes nothing
    assert _reorder(formatted) == formatted
    # the linter no longer complains about ordering
    ordering_problems = [
        problem
        for problem in lint_code(formatted)
        if problem.name == "class-definitions-order"
    ]
    assert ordering_problems == []


def test_reorder_disabled_by_default():
    code = "var x = 1\nsignal s\n"
    formatted = format_code(code, max_line_length=MAX_LINE_LENGTH)
    assert formatted.index("var x") < formatted.index("signal s")


def test_reorder_with_spaces_for_indent():
    code = "func foo():\n\tpass\nsignal s\n"
    formatted = _reorder(code, spaces_for_indent=4)
    check_formatting_safety(
        code, formatted, MAX_LINE_LENGTH, spaces_for_indent=4, reorder_code=True
    )
    assert formatted.index("signal s") < formatted.index("func foo")
    assert "\n    pass" in formatted
