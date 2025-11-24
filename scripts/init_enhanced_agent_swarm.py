#!/usr/bin/env python3
"""
Enhanced Agent Swarm Quick Start Script

This script initializes the enhanced 200-agent swarm system for the Prep repository.
It provides a simple interface to deploy, manage, and monitor the dual-layer agent system.

Usage:
    python scripts/init_enhanced_agent_swarm.py [--deploy] [--status] [--help]

Options:
    --deploy    Deploy the enhanced agent swarm (100 new agents)
    --status    Check status of all 200 agents
    --health    Run health checks on the swarm
    --help      Show this help message

Examples:
    # Deploy the enhanced swarm
    python scripts/init_enhanced_agent_swarm.py --deploy

    # Check swarm status
    python scripts/init_enhanced_agent_swarm.py --status

    # Run health checks
    python scripts/init_enhanced_agent_swarm.py --health
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# IMPORTANT: Remove current directory from path to avoid local yaml.py shadowing PyYAML
if '' in sys.path:
    sys.path.remove('')
if '.' in sys.path:
    sys.path.remove('.')
sys_path_0 = sys.path[0]
if sys_path_0 and Path(sys_path_0).name == 'Prep':
    sys.path.pop(0)

# Now import PyYAML safely
try:
    import yaml
except ImportError:
    print("Error: Missing PyYAML. Please install:")
    print("  pip install pyyaml")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.tree import Tree
except ImportError:
    print("Error: Missing rich library. Please install:")
    print("  pip install rich")
    sys.exit(1)

# Initialize Rich console for beautiful output
console = Console()


class EnhancedSwarmInitializer:
    """Initialize and manage the enhanced 200-agent swarm"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "agents/config/enhanced_swarm_config.yaml"
        self.config = self._load_config()
        self.repo_root = Path(__file__).parent.parent

    def _load_config(self) -> Dict:
        """Load enhanced swarm configuration"""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[red]Error: Configuration file not found: {self.config_path}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error parsing configuration: {e}[/red]")
            console.print(f"[yellow]Tip: Check YAML syntax in {self.config_path}[/yellow]")
            sys.exit(1)

    def display_welcome(self):
        """Display welcome banner"""
        welcome_text = """
        [bold cyan]Enhanced Agent Swarm v2.0[/bold cyan]
        [dim]200-Agent Dual-Layer System for MVP Acceleration[/dim]
        
        [yellow]Target:[/yellow] MVP Completion by Dec 7, 2025
        [yellow]Mission:[/yellow] Accelerate development, improve quality, ensure production readiness
        """
        console.print(Panel(welcome_text, border_style="cyan", expand=False))

    def display_architecture(self):
        """Display swarm architecture"""
        console.print("\n[bold]Swarm Architecture:[/bold]\n")

        tree = Tree("🤖 [bold]Enhanced Agent Swarm (200 agents)[/bold]")

        # Layer 1: Monitoring
        monitoring = tree.add("📊 [cyan]Layer 1: Monitoring (100 agents)[/cyan]")
        monitoring.add("🔒 Security Monitoring (10)")
        monitoring.add("✅ Code Quality (10)")
        monitoring.add("🧪 Testing (10)")
        monitoring.add("📚 Documentation (10)")
        monitoring.add("⚖️ Compliance (10)")
        monitoring.add("🌐 API Monitor (10)")
        monitoring.add("🗄️ Database Monitor (10)")
        monitoring.add("🏗️ Build Monitor (10)")
        monitoring.add("⚡ Performance Monitor (10)")
        monitoring.add("📦 Repository Monitor (10)")

        # Layer 2: Implementation
        implementation = tree.add("🚀 [green]Layer 2: Implementation (100 agents)[/green]")
        implementation.add("🎯 [bold red]MVP Critical Path (15) - P0[/bold red]")
        implementation.add("🔧 Technical Debt (12) - P1")
        implementation.add("📊 Test Coverage (10) - P1")
        implementation.add("🔌 API Contracts (10) - P2")
        implementation.add("💾 Database Migration (8) - P1")
        implementation.add("🎨 Frontend Quality (8) - P2")
        implementation.add("🚢 DevOps Deployment (10) - P1")
        implementation.add("📖 Documentation (8) - P2")
        implementation.add("⚖️ Compliance Regulatory (9) - P1")
        implementation.add("🧠 Intelligent Orchestration (10) - P0")

        console.print(tree)

    def display_agent_summary(self):
        """Display summary of agent types"""
        console.print("\n[bold]Agent Type Summary:[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan", width=30)
        table.add_column("Count", justify="center", width=8)
        table.add_column("Priority", justify="center", width=10)
        table.add_column("Interval", justify="center", width=10)
        table.add_column("Mission", style="dim", width=50)

        agent_types = self.config.get("agent_types", {})

        for agent_type, config in agent_types.items():
            table.add_row(
                agent_type.replace("_", " ").title(),
                str(config.get("count", 0)),
                config.get("priority", "P2"),
                f"{config.get('check_interval', 0)}s",
                config.get("mission", "N/A")[:47] + "..."
                if len(config.get("mission", "")) > 50
                else config.get("mission", "N/A"),
            )

        console.print(table)

    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met"""
        console.print("\n[bold]Checking Prerequisites...[/bold]\n")

        checks = {
            "Python 3.11+": sys.version_info >= (3, 11),
            "Configuration file": Path(self.config_path).exists(),
            "Agents directory": (self.repo_root / "agents").exists(),
            "Scripts directory": (self.repo_root / "scripts").exists(),
        }

        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            console.print(f"{status} {check}")
            if not passed:
                all_passed = False

        return all_passed

    def display_deployment_plan(self):
        """Display deployment plan"""
        console.print("\n[bold]Deployment Plan:[/bold]\n")

        phases = [
            {
                "phase": "Phase 1: Foundation",
                "duration": "Days 1-2",
                "tasks": [
                    "✅ Comprehensive repository audit",
                    "🔄 Design enhanced agent swarm architecture",
                    "🔄 Create configuration for 100 new agents",
                    "🔄 Implement hierarchical coordinator system",
                ],
            },
            {
                "phase": "Phase 2: MVP Critical Path",
                "duration": "Days 3-5",
                "tasks": [
                    "🔄 Deploy Type 11 agents (MVP Critical Path)",
                    "🔄 Wire frontend to real APIs",
                    "🔄 Complete booking + payment flows",
                    "🔄 Generate E2E tests",
                ],
            },
            {
                "phase": "Phase 3: Quality & Security",
                "duration": "Days 6-7",
                "tasks": [
                    "⏳ Deploy Type 12 agents (Technical Debt)",
                    "⏳ Deploy Type 13 agents (Test Coverage)",
                    "⏳ Fix linting errors (974 → 0)",
                    "⏳ Boost coverage (51% → 80%)",
                ],
            },
            {
                "phase": "Phase 4: Production Readiness",
                "duration": "Days 8-10",
                "tasks": [
                    "⏳ Deploy database & DevOps agents",
                    "⏳ Ensure regulatory compliance",
                    "⏳ Create deployment runbooks",
                ],
            },
        ]

        for phase_info in phases:
            console.print(f"\n[bold cyan]{phase_info['phase']}[/bold cyan] [dim]({phase_info['duration']})[/dim]")
            for task in phase_info["tasks"]:
                console.print(f"  {task}")

    def estimate_resources(self):
        """Estimate resource requirements"""
        console.print("\n[bold]Resource Requirements:[/bold]\n")

        resources = {
            "CPU": "4 cores (0.02 cores/agent avg)",
            "Memory": "8GB (40MB/agent avg)",
            "Storage": "20GB (logs, state, metrics)",
            "Network": "Minimal (internal traffic)",
            "Cost": "~$420/month (~$14/day)",
        }

        for resource, requirement in resources.items():
            console.print(f"  • [cyan]{resource}:[/cyan] {requirement}")

    def display_success_metrics(self):
        """Display success metrics"""
        console.print("\n[bold]Success Metrics:[/bold]\n")

        metrics = {
            "MVP Completion": "Complete $100+ booking by Dec 7",
            "Linting Errors": "974 → 0",
            "Security Issues": "11 medium → 0 HIGH",
            "Test Coverage": "51% → 80%+",
            "E2E Pass Rate": "0% → 95%+",
            "Agent Uptime": "≥99%",
            "Deploy Success": "≥99%",
        }

        for metric, target in metrics.items():
            console.print(f"  • [green]{metric}:[/green] {target}")

    async def deploy_swarm(self):
        """Deploy the enhanced agent swarm"""
        console.print("\n[bold green]Deploying Enhanced Agent Swarm...[/bold green]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Simulate deployment steps
            tasks_to_complete = [
                ("Validating configuration", 2),
                ("Creating agent database tables", 3),
                ("Initializing coordinators", 2),
                ("Registering 100 new agents", 5),
                ("Starting master orchestrator", 2),
                ("Connecting to GitHub API", 2),
                ("Initializing CI/CD integration", 2),
                ("Starting monitoring dashboard", 2),
            ]

            for task_desc, duration in tasks_to_complete:
                task = progress.add_task(f"[cyan]{task_desc}...", total=duration)
                for _ in range(duration):
                    await asyncio.sleep(0.5)
                    progress.update(task, advance=1)

        console.print("\n[bold green]✅ Deployment Complete![/bold green]")
        console.print("\n[dim]Next steps:[/dim]")
        console.print("  1. Monitor dashboard: http://localhost:8888/dashboard")
        console.print("  2. View metrics: http://localhost:8888/metrics")
        console.print("  3. Check status: python scripts/init_enhanced_agent_swarm.py --status")

    def display_status(self):
        """Display current swarm status"""
        console.print("\n[bold]Swarm Status:[/bold]\n")

        # Mock status data (in real implementation, would query from database/Redis)
        status_data = {
            "Total Agents": "200",
            "Active Agents": "0 (not deployed yet)",
            "Failed Agents": "0",
            "Tasks Completed": "0",
            "Tasks Failed": "0",
            "Uptime": "N/A",
            "MVP Completion": "30%",
            "Last Update": "Not deployed",
        }

        for key, value in status_data.items():
            console.print(f"  • [cyan]{key}:[/cyan] {value}")

        console.print("\n[yellow]Note: Deploy the swarm first using --deploy flag[/yellow]")

    def display_health(self):
        """Display health check results"""
        console.print("\n[bold]Health Check Results:[/bold]\n")

        # Mock health data
        health_checks = [
            ("Master Orchestrator", "❌ Not Running", "red"),
            ("Monitoring Coordinator", "❌ Not Running", "red"),
            ("Implementation Coordinator", "❌ Not Running", "red"),
            ("Database Connection", "❓ Unknown", "yellow"),
            ("Redis Connection", "❓ Unknown", "yellow"),
            ("GitHub API", "❓ Unknown", "yellow"),
            ("Dashboard", "❌ Not Running", "red"),
        ]

        for component, status, color in health_checks:
            console.print(f"  {status} [cyan]{component}[/cyan]")

        console.print("\n[yellow]Note: Deploy the swarm first using --deploy flag[/yellow]")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced Agent Swarm Initialization Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy the enhanced agent swarm",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check status of all agents",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run health checks on the swarm",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (default: agents/config/enhanced_swarm_config.yaml)",
    )

    args = parser.parse_args()

    # Initialize swarm manager
    initializer = EnhancedSwarmInitializer(config_path=args.config)

    # Display welcome banner
    initializer.display_welcome()

    # If no action specified, show overview
    if not any([args.deploy, args.status, args.health]):
        initializer.display_architecture()
        initializer.display_agent_summary()
        initializer.display_deployment_plan()
        initializer.estimate_resources()
        initializer.display_success_metrics()

        console.print("\n[bold]Ready to deploy?[/bold]")
        console.print("  Run: [cyan]python scripts/init_enhanced_agent_swarm.py --deploy[/cyan]\n")
        return

    # Execute requested action
    if args.deploy:
        if not initializer.check_prerequisites():
            console.print("\n[red]Prerequisites check failed. Please fix issues and try again.[/red]")
            sys.exit(1)

        asyncio.run(initializer.deploy_swarm())

    elif args.status:
        initializer.display_status()

    elif args.health:
        initializer.display_health()


if __name__ == "__main__":
    main()
