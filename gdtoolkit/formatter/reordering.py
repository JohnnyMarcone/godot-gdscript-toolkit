"""Reorders class-level members so the output satisfies the linter's
``class-definitions-order`` rule.

This runs *after* a normal formatting pass, so the input here is already
canonical: one statement per line region, ``;``-joined statements split,
annotations on their own lines and comments placed. That lets us reorder by
moving whole contiguous line-blocks (which carry their leading comments,
annotations and trailing property bodies with them) and then reformat once more
to normalize the blank-line spacing between members.
"""
from typing import List

from lark import Tree, Token

from ..parser import parser
from ..common.ast import Statement, Annotation
from ..common.ordering import DEFAULT_CLASS_DEFINITIONS_ORDER, map_statement_to_section
from .annotation import is_non_standalone_annotation


# pylint: disable-next=too-few-public-methods
class _Member:
    """A reorderable class-level member: its anchor statement, the non-standalone
    annotations attached to it, and the last source line it occupies."""

    def __init__(self, anchor: Tree, annotations: List[Tree], end_line: int):
        self.anchor = anchor
        self.annotations = annotations
        self.end_line = end_line

    @property
    def kind(self) -> str:
        return self.anchor.data


def reorder_class_members(formatted_code: str) -> str:
    parse_tree = parser.parse(formatted_code, gather_metadata=True)
    lines = formatted_code.split("\n")
    reordered = _reorder_scope(
        parse_tree, 1, len(lines), lines, DEFAULT_CLASS_DEFINITIONS_ORDER
    )
    return "\n".join(reordered)


# pylint: disable-next=too-many-locals
def _reorder_scope(
    scope: Tree,
    body_start: int,
    body_end: int,
    lines: List[str],
    order: List[str],
) -> List[str]:
    members = _scan_members(_scope_body_children(scope))
    blocks = []  # type: List[tuple]
    cursor = body_start
    # Rank used for `pass` statements - they stick to the section they follow so
    # they never jump around (the ordering rule ignores them).
    running_rank = 0
    for index, member in enumerate(members):
        block_end = member.end_line
        if member.kind == "class_def":
            header_line = member.anchor.meta.line
            inner = _reorder_scope(
                member.anchor, header_line + 1, block_end, lines, order
            )
            block_lines = lines[cursor - 1 : header_line] + inner
            rank = order.index("others")
        elif member.kind == "pass_stmt":
            block_lines = lines[cursor - 1 : block_end]
            rank = running_rank
        else:
            block_lines = lines[cursor - 1 : block_end]
            rank = order.index(map_statement_to_section(_as_statement(member)))
            running_rank = rank
        blocks.append((rank, index, block_lines))
        cursor = block_end + 1

    tail = lines[cursor - 1 : body_end]
    blocks.sort(key=lambda block: (block[0], block[1]))

    result = []  # type: List[str]
    for _, _, block_lines in blocks:
        result += block_lines
    result += tail
    return result


def _scope_body_children(scope: Tree) -> List[Tree]:
    """Statement/annotation nodes forming a class body, in source order.

    For a nested ``class_def`` the class name token and any header ``extends``
    (which share the header line) are excluded - only body members are returned.
    """
    if scope.data == "class_def":
        header_line = scope.meta.line
        return [
            child
            for child in scope.children
            if isinstance(child, Tree) and child.meta.line > header_line
        ]
    return [child for child in scope.children if isinstance(child, Tree)]


def _scan_members(children: List[Tree]) -> List[_Member]:
    members = []  # type: List[_Member]
    pending_annotations = []  # type: List[Tree]
    for node in children:
        if node.data == "annotation":
            if node.children[0].value == "tool":
                members.append(_Member(node, [], node.meta.end_line))
            elif is_non_standalone_annotation(node):
                pending_annotations.append(node)
            # Other standalone annotations (@export_group, @icon, @abstract, ...)
            # decorate the following member and ride along as its leading lines.
            continue
        if node.data == "property_body_def":
            if members:
                members[-1].end_line = _last_content_line(node)
            continue
        members.append(
            _Member(node, list(pending_annotations), _last_content_line(node))
        )
        pending_annotations = []
    return members


def _last_content_line(node: Tree) -> int:
    """Last source line actually occupied by ``node``.

    ``meta.end_line`` is unreliable here: lark inflates it with trailing blank
    lines and ``_DEDENT`` tokens (e.g. a function's ``end_line`` can point at the
    next statement). The largest line among real descendant tokens, falling back
    to each subtree's start line, gives the true last line of content.
    """
    last_line = node.meta.line
    for child in node.children:
        if isinstance(child, Token):
            last_line = max(last_line, child.end_line)
        elif isinstance(child, Tree):
            last_line = max(last_line, _last_content_line(child))
    return last_line


def _as_statement(member: _Member) -> Statement:
    return Statement(
        member.anchor, [Annotation(annotation) for annotation in member.annotations]
    )
