from functools import partial
from types import MappingProxyType
from typing import List

from lark import Tree

from ..common.ast import AbstractSyntaxTree, Class
from ..common.ordering import is_statement_irrelevant, map_statement_to_section
from ..common.utils import get_line, get_column

from .problem import Problem


def lint(parse_tree: Tree, config: MappingProxyType) -> List[Problem]:
    disable = config["disable"]
    checks_to_run_w_ast = [
        (
            "class-definitions-order",
            partial(_class_definitions_order_check, config["class-definitions-order"]),
        ),
    ]
    ast = AbstractSyntaxTree(parse_tree)
    problem_clusters = (
        function(ast) if name not in disable else []
        for name, function in checks_to_run_w_ast
    )
    return [problem for cluster in problem_clusters for problem in cluster]


def _class_definitions_order_check(
    order: List[str], ast: AbstractSyntaxTree
) -> List[Problem]:
    return [
        problem
        for a_class in ast.all_classes
        for problem in _class_definitions_order_check_for_class(a_class, order)
    ]


def _class_definitions_order_check_for_class(
    a_class: Class, order: List[str]
) -> List[Problem]:
    problems = []
    current_section = order[0]
    for statement in a_class.statements:
        if is_statement_irrelevant(statement):
            continue
        try:
            current_section_rank = order.index(current_section)
            statement_section = map_statement_to_section(statement)
            section_rank = order.index(statement_section)
            if section_rank >= current_section_rank:
                current_section = statement_section
            else:
                problems.append(
                    Problem(
                        name="class-definitions-order",
                        description="Definition out of order in {}".format(
                            a_class.name
                        ),
                        line=get_line(statement.lark_node),
                        column=get_column(statement.lark_node),
                    )
                )
        except ValueError:
            problems.append(
                Problem(
                    name="class-definitions-order",
                    description=" ".join(
                        [
                            "Definition order not specified for '{}' or '{}',",
                            "please fix/re-generate your gdlintrc file",
                        ]
                    ).format(current_section, statement_section),
                    line=get_line(statement.lark_node),
                    column=get_column(statement.lark_node),
                )
            )
    return problems
