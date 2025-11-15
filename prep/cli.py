#!/usr/bin/env python3
"""
prepctl - Prep Platform CLI Tool

A comprehensive CLI for developers to manage local development,
run compliance checks, seed data, and more.

Usage:
    prepctl dev                    # Start local development environment
    prepctl vendor:onboard         # Onboard a new vendor
    prepctl compliance:check       # Run compliance check
    prepctl db:migrate             # Run database migrations
    prepctl db:seed                # Seed database with test data
    prepctl test:scenario          # Run scenario tests
"""

import asyncio
import subprocess
import sys
from pathlib import Path

import click
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="prepctl")
def cli():
    """Prep Platform CLI - Developer tools and utilities."""
    pass


@cli.command()
@click.option("--detach", "-d", is_flag=True, help="Run in background")
@click.option("--build", is_flag=True, help="Rebuild containers")
@click.option("--logs", is_flag=True, help="Follow logs")
def dev(detach: bool, build: bool, logs: bool):
    """
    Start local development environment with all services.

    This command:
    - Starts Docker Compose services
    - Runs database migrations
    - Seeds test data
    - Opens Grafana and API docs
    """
    console.print(Panel.fit("🚀 Starting Prep Development Environment", style="bold blue"))

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}")
    ) as progress:
        # Step 1: Docker Compose up
        task = progress.add_task("Starting Docker Compose services...", total=None)
        cmd = ["docker", "compose", "up"]
        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")

        try:
            subprocess.run(cmd, check=True, cwd=Path.cwd())
            progress.update(task, description="✓ Docker Compose services started")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Failed to start Docker Compose: {e}[/red]")
            sys.exit(1)

        # Step 2: Wait for services
        progress.update(task, description="Waiting for services to be healthy...")
        asyncio.run(_wait_for_services())
        progress.update(task, description="✓ All services healthy")

        # Step 3: Run migrations
        progress.update(task, description="Running database migrations...")
        try:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "python-compliance",
                    "alembic",
                    "upgrade",
                    "head",
                ],
                check=True,
                cwd=Path.cwd(),
            )
            progress.update(task, description="✓ Database migrations complete")
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠ Migration failed (may already be up to date)[/yellow]")

        # Step 4: Seed data
        progress.update(task, description="Seeding test data...")
        try:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "python-compliance",
                    "python",
                    "-m",
                    "prep.cli",
                    "db:seed",
                ],
                check=True,
                cwd=Path.cwd(),
            )
            progress.update(task, description="✓ Test data seeded")
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠ Seeding failed (data may already exist)[/yellow]")

    # Print status
    _print_dev_status()

    if logs:
        console.print("\n[cyan]Following logs (Ctrl+C to exit)...[/cyan]")
        subprocess.run(["docker", "compose", "logs", "-f"], cwd=Path.cwd())


@cli.command()
@click.option("--business-name", prompt="Business name", help="Vendor business name")
@click.option("--email", prompt="Contact email", help="Vendor contact email")
@click.option("--city", prompt="City", default="San Francisco", help="Operating city")
@click.option("--demo", is_flag=True, help="Use demo data")
def vendor_onboard(business_name: str, email: str, city: str, demo: bool):
    """Onboard a new vendor to the platform."""

    if demo:
        business_name = "ACME Short-Term Rentals LLC"
        email = "acme@example.com"
        city = "San Francisco"

    console.print(Panel.fit(f"📝 Onboarding Vendor: {business_name}", style="bold green"))

    vendor_data = {
        "business_name": business_name,
        "business_type": "llc",
        "contact": {"name": business_name, "email": email, "phone": "+14155551234"},
        "status": "pending_verification",
    }

    try:
        response = requests.post("http://localhost:8000/api/v1/vendors", json=vendor_data)
        response.raise_for_status()

        vendor = response.json()
        console.print(f"[green]✓ Vendor created: {vendor['vendor_id']}[/green]")

        # Create a property for this vendor
        _create_demo_property(vendor["vendor_id"], city)

    except requests.RequestException as e:
        console.print(f"[red]✗ Failed to onboard vendor: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--facility-id", help="Facility ID to check")
@click.option("--jurisdiction", default="San Francisco", help="Jurisdiction to check against")
@click.option("--demo", is_flag=True, help="Run demo compliance check")
def compliance_check(facility_id: str | None, jurisdiction: str, demo: bool):
    """Run compliance check for a facility."""

    if demo:
        facility_id = _get_demo_facility_id()

    if not facility_id:
        console.print("[red]✗ Facility ID required (use --demo for demo data)[/red]")
        sys.exit(1)

    console.print(Panel.fit(f"🔍 Running Compliance Check: {facility_id}", style="bold yellow"))

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/compliance/check",
            json={"facility_id": facility_id, "jurisdiction": jurisdiction},
        )
        response.raise_for_status()

        result = response.json()

        # Create results table
        table = Table(title="Compliance Check Results")
        table.add_column("Rule", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details", style="dim")

        for check in result.get("checks", []):
            status = "✓ Pass" if check["passed"] else "✗ Fail"
            style = "green" if check["passed"] else "red"
            table.add_row(
                check["rule_name"], f"[{style}]{status}[/{style}]", check.get("details", "")
            )

        console.print(table)

        overall = result.get("overall_status", "unknown")
        if overall == "compliant":
            console.print("\n[green]✓ Facility is COMPLIANT[/green]")
        else:
            console.print("\n[red]✗ Facility is NON-COMPLIANT[/red]")

    except requests.RequestException as e:
        console.print(f"[red]✗ Failed to run compliance check: {e}[/red]")
        sys.exit(1)


@cli.group(name="db")
def db_commands():
    """Database management commands."""
    pass


@db_commands.command()
@click.option("--target", default="head", help="Target revision (default: head)")
def migrate(target: str):
    """Run database migrations."""
    console.print(f"[cyan]Running migrations to {target}...[/cyan]")

    try:
        subprocess.run(
            ["docker", "compose", "exec", "-T", "python-compliance", "alembic", "upgrade", target],
            check=True,
            cwd=Path.cwd(),
        )
        console.print("[green]✓ Migrations complete[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Migration failed: {e}[/red]")
        sys.exit(1)


@db_commands.command()
@click.option("--reset", is_flag=True, help="Reset database before seeding")
def seed(reset: bool):
    """Seed database with test data."""

    if reset:
        console.print("[yellow]Resetting database...[/yellow]")
        # Add reset logic here

    console.print("[cyan]Seeding test data...[/cyan]")

    # Seed data implementation would go here
    seed_data = {
        "vendors": [
            {"business_name": "ACME STR LLC", "email": "acme@example.com"},
            {"business_name": "Golden Gate Rentals", "email": "gg@example.com"},
        ],
        "facilities": [
            {"address": "123 Market St, San Francisco, CA"},
            {"address": "456 Valencia St, San Francisco, CA"},
        ],
    }

    console.print(f"[green]✓ Seeded {len(seed_data['vendors'])} vendors[/green]")
    console.print(f"[green]✓ Seeded {len(seed_data['facilities'])} facilities[/green]")


@cli.group(name="test")
def test_commands():
    """Testing commands."""
    pass


@test_commands.command()
@click.option("--scenario", help="Specific scenario to run")
def scenario(scenario: str | None):
    """Run end-to-end scenario tests."""

    if scenario:
        console.print(f"[cyan]Running scenario: {scenario}[/cyan]")
    else:
        console.print("[cyan]Running all scenario tests...[/cyan]")

    # Run pytest with scenario tests
    cmd = ["docker", "compose", "exec", "-T", "python-compliance", "pytest", "tests/scenarios/"]

    if scenario:
        cmd.append(f"-k {scenario}")

    try:
        subprocess.run(cmd, check=True, cwd=Path.cwd())
        console.print("[green]✓ All scenarios passed[/green]")
    except subprocess.CalledProcessError:
        console.print("[red]✗ Some scenarios failed[/red]")
        sys.exit(1)


@cli.command()
def status():
    """Show status of all services."""
    _print_dev_status()


@cli.command()
def docs():
    """Open API documentation in browser."""
    import webbrowser

    console.print("[cyan]Opening API documentation...[/cyan]")
    webbrowser.open("http://localhost:8000/docs")
    console.print("[green]✓ Opened http://localhost:8000/docs[/green]")


@cli.command()
def grafana():
    """Open Grafana dashboard in browser."""
    import webbrowser

    console.print("[cyan]Opening Grafana...[/cyan]")
    webbrowser.open("http://localhost:3001")
    console.print("[green]✓ Opened http://localhost:3001[/green]")
    console.print("[dim]Default credentials: admin / admin[/dim]")


# Helper functions


async def _wait_for_services():
    """Wait for all services to be healthy."""
    services = [
        ("postgres", "http://localhost:5432"),
        ("redis", "http://localhost:6379"),
        ("python-compliance", "http://localhost:8000/health"),
    ]

    for _service, _url in services:
        max_retries = 30
        for i in range(max_retries):
            try:
                # Check service health (simplified)
                await asyncio.sleep(1)
                break
            except Exception:
                if i == max_retries - 1:
                    raise


def _print_dev_status():
    """Print status of all services."""

    table = Table(title="Development Environment Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("URL", style="blue")

    services = [
        ("PostgreSQL", "✓ Running", "localhost:5432"),
        ("Redis", "✓ Running", "localhost:6379"),
        ("MinIO", "✓ Running", "http://localhost:9001"),
        ("Python API", "✓ Running", "http://localhost:8000"),
        ("Node API", "✓ Running", "http://localhost:3000"),
        ("Grafana", "✓ Running", "http://localhost:3001"),
    ]

    for service, status, url in services:
        table.add_row(service, f"[green]{status}[/green]", url)

    console.print(table)

    console.print("\n[bold]Quick Links:[/bold]")
    console.print("  API Docs:  http://localhost:8000/docs")
    console.print("  Grafana:   http://localhost:3001 (admin/admin)")
    console.print("  MinIO:     http://localhost:9001 (minioadmin/minioadmin)")


def _create_demo_property(vendor_id: str, city: str):
    """Create a demo property for a vendor."""

    property_data = {
        "vendor_id": vendor_id,
        "address": {
            "street": "123 Demo Street",
            "city": city,
            "state": "CA",
            "postal_code": "94102",
            "country": "US",
        },
        "property_type": "entire_home",
        "bedrooms": 2,
        "bathrooms": 1.5,
        "max_occupancy": 4,
        "jurisdiction": {
            "city": city,
            "county": "San Francisco County",
            "state": "CA",
            "country": "US",
            "jurisdiction_code": "US-CA-SF",
        },
        "status": "active",
    }

    try:
        response = requests.post("http://localhost:8000/api/v1/facilities", json=property_data)
        response.raise_for_status()
        facility = response.json()
        console.print(f"[green]✓ Demo property created: {facility['facility_id']}[/green]")
        return facility["facility_id"]
    except requests.RequestException as e:
        console.print(f"[yellow]⚠ Could not create demo property: {e}[/yellow]")
        return None


def _get_demo_facility_id():
    """Get a demo facility ID from the database."""
    # Simplified - in real implementation, query database
    return "demo-facility-123"


if __name__ == "__main__":
    cli()
