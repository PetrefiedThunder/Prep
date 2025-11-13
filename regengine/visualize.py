#!/usr/bin/env python3
"""
RegEngine DAG Visualizer

Generates visual dependency graphs for compliance rules.

Usage:
    python regengine/visualize.py --jurisdiction san_francisco --output sf_dag.png
    python regengine/visualize.py --jurisdiction san_francisco --format dot
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


class RuleDAG:
    """Directed Acyclic Graph of compliance rules."""

    def __init__(self, jurisdiction: str):
        self.jurisdiction = jurisdiction
        self.rules = []
        self.dependencies = defaultdict(list)
        self.load_rules()

    def load_rules(self):
        """Load rules from YAML file."""
        rules_path = Path(__file__).parent / "cities" / self.jurisdiction / "rules.yaml"

        if not rules_path.exists():
            print(f"Error: Rules not found for jurisdiction '{self.jurisdiction}'")
            sys.exit(1)

        with open(rules_path) as f:
            data = yaml.safe_load(f)
            self.rules = data.get("rules", [])

        # Build dependency graph
        for rule in self.rules:
            rule_id = rule["id"]
            deps = rule.get("dependencies", [])
            for dep in deps:
                self.dependencies[dep].append(rule_id)

    def get_root_rules(self) -> list[dict[str, Any]]:
        """Get rules with no dependencies."""
        all_rule_ids = {rule["id"] for rule in self.rules}
        dependent_rules = set()
        for deps in self.dependencies.values():
            dependent_rules.update(deps)

        root_ids = all_rule_ids - dependent_rules
        return [rule for rule in self.rules if rule["id"] in root_ids]

    def get_rule_by_id(self, rule_id: str) -> dict[str, Any] | None:
        """Get rule by ID."""
        for rule in self.rules:
            if rule["id"] == rule_id:
                return rule
        return None

    def topological_sort(self) -> list[str]:
        """Return rules in topological order (dependencies first)."""
        visited = set()
        order = []

        def visit(rule_id: str):
            if rule_id in visited:
                return
            visited.add(rule_id)

            rule = self.get_rule_by_id(rule_id)
            if rule:
                for dep in rule.get("dependencies", []):
                    visit(dep)

            order.append(rule_id)

        for rule in self.rules:
            visit(rule["id"])

        return order

    def to_dot(self) -> str:
        """Generate Graphviz DOT format."""
        lines = ["digraph ComplianceRules {"]
        lines.append('    rankdir=TB;')
        lines.append('    node [shape=box, style=rounded];')
        lines.append('')

        # Define nodes with colors
        for rule in self.rules:
            rule_id = rule["id"]
            name = rule["name"]
            severity = rule["severity"]

            # Color by severity
            if severity == "blocking":
                color = "lightcoral"
            elif severity == "warning":
                color = "lightyellow"
            else:
                color = "lightblue"

            label = f"{rule_id}\\n{name}"
            lines.append(f'    "{rule_id}" [label="{label}", fillcolor="{color}", style=filled];')

        lines.append('')

        # Define edges
        for rule in self.rules:
            rule_id = rule["id"]
            for dep in rule.get("dependencies", []):
                lines.append(f'    "{dep}" -> "{rule_id}";')

        lines.append('}')
        return '\n'.join(lines)

    def to_ascii(self) -> str:
        """Generate ASCII tree representation."""
        lines = []
        lines.append(f"Compliance Rule DAG: {self.jurisdiction.upper()}")
        lines.append("=" * 60)
        lines.append("")

        visited = set()

        def print_rule(rule_id: str, indent: int = 0, prefix: str = ""):
            if rule_id in visited:
                return
            visited.add(rule_id)

            rule = self.get_rule_by_id(rule_id)
            if not rule:
                return

            severity_icon = "🔴" if rule["severity"] == "blocking" else "🟡" if rule["severity"] == "warning" else "🔵"
            lines.append(f"{' ' * indent}{prefix}[{rule_id}] {rule['name']} {severity_icon}")

            # Print children
            children = self.dependencies.get(rule_id, [])
            for i, child_id in enumerate(children):
                is_last = i == len(children) - 1
                child_prefix = "└── " if is_last else "├── "
                print_rule(child_id, indent + 4, child_prefix)

        # Start with root rules
        root_rules = self.get_root_rules()
        for rule in root_rules:
            print_rule(rule["id"])
            lines.append("")

        return '\n'.join(lines)

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram format."""
        lines = ["graph TB"]

        # Define nodes
        for rule in self.rules:
            rule_id = rule["id"].replace("-", "_")
            name = rule["name"].replace('"', "'")
            lines.append(f'    {rule_id}["{name}"]')

        # Define edges
        for rule in self.rules:
            rule_id = rule["id"].replace("-", "_")
            for dep in rule.get("dependencies", []):
                dep_id = dep.replace("-", "_")
                lines.append(f'    {dep_id} --> {rule_id}')

        return '\n'.join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get DAG statistics."""
        root_rules = self.get_root_rules()
        blocking_count = len([r for r in self.rules if r["severity"] == "blocking"])
        warning_count = len([r for r in self.rules if r["severity"] == "warning"])
        info_count = len([r for r in self.rules if r["severity"] == "info"])

        return {
            "total_rules": len(self.rules),
            "root_rules": len(root_rules),
            "blocking_rules": blocking_count,
            "warning_rules": warning_count,
            "info_rules": info_count,
            "max_depth": self._calculate_max_depth(),
        }

    def _calculate_max_depth(self) -> int:
        """Calculate maximum dependency depth."""
        max_depth = 0

        def get_depth(rule_id: str) -> int:
            rule = self.get_rule_by_id(rule_id)
            if not rule:
                return 0

            deps = rule.get("dependencies", [])
            if not deps:
                return 0

            return 1 + max(get_depth(dep) for dep in deps)

        for rule in self.rules:
            depth = get_depth(rule["id"])
            max_depth = max(max_depth, depth)

        return max_depth


def main():
    parser = argparse.ArgumentParser(description="Visualize RegEngine compliance rule DAGs")
    parser.add_argument("--jurisdiction", required=True, help="Jurisdiction ID (e.g., san_francisco)")
    parser.add_argument("--output", help="Output file path (PNG requires graphviz)")
    parser.add_argument(
        "--format",
        choices=["ascii", "dot", "mermaid"],
        default="ascii",
        help="Output format"
    )
    parser.add_argument("--stats", action="store_true", help="Show DAG statistics")

    args = parser.parse_args()

    # Build DAG
    dag = RuleDAG(args.jurisdiction)

    # Show stats if requested
    if args.stats:
        stats = dag.get_stats()
        print(f"Jurisdiction: {args.jurisdiction}")
        print(f"Total rules: {stats['total_rules']}")
        print(f"  Blocking: {stats['blocking_rules']}")
        print(f"  Warning: {stats['warning_rules']}")
        print(f"  Info: {stats['info_rules']}")
        print(f"Root rules: {stats['root_rules']}")
        print(f"Max dependency depth: {stats['max_depth']}")
        print()

    # Generate output
    if args.format == "ascii":
        output = dag.to_ascii()
    elif args.format == "dot":
        output = dag.to_dot()
    elif args.format == "mermaid":
        output = dag.to_mermaid()

    # Write to file or stdout
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Output written to {args.output}")

        # If output is PNG and format is dot, try to render with graphviz
        if args.output.endswith(".png") and args.format == "dot":
            try:
                import subprocess
                dot_file = args.output.replace(".png", ".dot")
                with open(dot_file, "w") as f:
                    f.write(output)
                subprocess.run(["dot", "-Tpng", dot_file, "-o", args.output], check=True)
                print(f"Rendered PNG: {args.output}")
            except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
                print("Warning: Could not render PNG. Install graphviz to generate images.")
    else:
        print(output)


if __name__ == "__main__":
    main()
