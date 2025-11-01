"""Generate Graphviz representations of SF compliance rules."""

from __future__ import annotations

import argparse
import ast
import inspect
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from apps.sf_regulatory_service.config import get_compliance_config
from apps.sf_regulatory_service.services import ComplianceEvaluator


@dataclass
class RuleGraph:
    """Minimal directed graph structure for compliance decision flows."""

    nodes: Dict[str, str] = field(default_factory=dict)
    edges: Set[Tuple[str, str]] = field(default_factory=set)
    order: List[str] = field(default_factory=list)

    def add_node(self, label: str, kind: str) -> str:
        if label not in self.nodes:
            self.nodes[label] = kind
            self.order.append(label)
        return label

    def add_edge(self, source: str, target: str) -> None:
        if source == target:
            return
        self.edges.add((source, target))

    def to_dot(self, graph_name: str = "SFCompliance") -> str:
        shape_by_kind = {
            "start": "Mdiamond",
            "condition": "diamond",
            "issue": "box",
            "status": "ellipse",
            "other": "oval",
        }
        lines = [f"digraph {graph_name} {{", "    rankdir=LR;"]
        for label in self.order:
            kind = self.nodes.get(label, "other")
            shape = shape_by_kind.get(kind, "oval")
            safe_label = label.replace("\"", "\\\"")
            lines.append(f'    "{safe_label}" [shape={shape}];')
        for source, target in sorted(self.edges):
            safe_source = source.replace("\"", "\\\"")
            safe_target = target.replace("\"", "\\\"")
            lines.append(f'    "{safe_source}" -> "{safe_target}";')
        lines.append("}")
        return "\n".join(lines)


def _load_evaluator() -> ComplianceEvaluator:
    config = get_compliance_config()
    return ComplianceEvaluator(config)


def _build_graph_from_function(func) -> RuleGraph:
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    func_def = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef)),
        None,
    )
    if func_def is None:
        raise ValueError("Could not locate function definition for evaluator")

    graph = RuleGraph()
    graph.add_node("Start", "start")

    def process_block(statements: Sequence[ast.stmt], stack: Sequence[str]) -> None:
        for stmt in statements:
            if isinstance(stmt, ast.If):
                handle_if(stmt, stack)
            elif _is_issue_append(stmt):
                label = _issue_label(stmt)
                node = graph.add_node(label, "issue")
                graph.add_edge(stack[-1], node)
            elif _is_status_assignment(stmt):
                label = _status_label(stmt)
                node = graph.add_node(label, "status")
                graph.add_edge(stack[-1], node)
            elif isinstance(stmt, ast.For):
                process_block(stmt.body, stack)
                process_block(stmt.orelse, stack)
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                process_block(stmt.body, stack)
            elif isinstance(stmt, ast.Try):
                process_block(stmt.body, stack)
                for handler in stmt.handlers:
                    process_block(handler.body, stack)
                process_block(stmt.orelse, stack)
                process_block(stmt.finalbody, stack)
            else:
                continue

    def handle_if(node: ast.If, stack: Sequence[str]) -> None:
        condition = textwrap.dedent(ast.unparse(node.test)).strip()
        cond_node = graph.add_node(condition, "condition")
        graph.add_edge(stack[-1], cond_node)
        process_block(node.body, list(stack) + [cond_node])
        if node.orelse:
            # Chain of elif statements
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                handle_if(node.orelse[0], stack)
            else:
                else_label = f"else: {condition}"
                else_node = graph.add_node(else_label, "condition")
                graph.add_edge(stack[-1], else_node)
                process_block(node.orelse, list(stack) + [else_node])

    process_block(func_def.body, ["Start"])
    return graph


def _is_issue_append(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    call = stmt.value
    if not isinstance(call.func, ast.Attribute):
        return False
    return (
        isinstance(call.func.value, ast.Name)
        and call.func.value.id == "issues"
        and call.func.attr == "append"
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    )


def _issue_label(stmt: ast.stmt) -> str:
    call = stmt.value  # type: ignore[assignment]
    message = call.args[0].value  # type: ignore[index]
    return f"Issue: {message}"


def _is_status_assignment(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Assign):
        return False
    if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
        return False
    target = stmt.targets[0]
    return (
        target.id == "status"
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _status_label(stmt: ast.Assign) -> str:
    value = stmt.value.value  # type: ignore[assignment]
    return f"status = \"{value}\""


def build_sf_compliance_graph() -> RuleGraph:
    """Return a graph representation for the SF compliance evaluator."""
    evaluator = _load_evaluator()
    return _build_graph_from_function(evaluator.evaluate)


def render_svg(dot: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from graphviz import Source  # type: ignore
    except Exception:
        dot_executable = shutil.which("dot")
        if not dot_executable:
            raise RuntimeError("Graphviz is required to render SVG output")
        completed = subprocess.run(
            [dot_executable, "-Tsvg"],
            input=dot.encode("utf-8"),
            check=True,
            stdout=subprocess.PIPE,
        )
        output_path.write_bytes(completed.stdout)
        return
    source = Source(dot)
    source.render(outfile=str(output_path), format="svg", cleanup=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dot",
        type=Path,
        help="Optional path to write the Graphviz DOT output.",
    )
    parser.add_argument(
        "--write-svg",
        action="store_true",
        help="Render docs/architecture/SF_validation_flow.svg alongside DOT output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    graph = build_sf_compliance_graph()
    dot = graph.to_dot()
    args = parse_args(argv)
    if args.output_dot:
        args.output_dot.parent.mkdir(parents=True, exist_ok=True)
        args.output_dot.write_text(dot, encoding="utf-8")
    else:
        print(dot)
    if args.write_svg:
        output_path = Path("docs/architecture/SF_validation_flow.svg")
        render_svg(dot, output_path)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI invocation
    raise SystemExit(main())
