"""Additional specialized agent implementations for infrastructure monitoring.

This module contains agent implementations for API, database, build,
performance, and repository monitoring with real integrations.
"""

import asyncio
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

from ..core.agent import Agent


async def http_check(url: str, timeout: int = 10) -> tuple[bool, int, float]:
    """Perform HTTP health check and return (success, status_code, response_time)."""
    try:
        start = asyncio.get_event_loop().time()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                elapsed = asyncio.get_event_loop().time() - start
                return resp.status < 500, resp.status, elapsed
    except Exception:
        return False, 0, timeout


class APIMonitorAgent(Agent):
    """Agent for monitoring API health and performance.

    Monitors:
    - Health check endpoints
    - Response times
    - Error rates from logs
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.health_endpoints = [
            "/healthz",
            "/health",
            "/api/v1/health",
        ]

    async def execute(self) -> None:
        """Execute API monitoring tasks."""
        self.logger.info(f"API monitor agent {self.config.name} checking APIs")

        await self._check_endpoint_health()
        await self._check_response_times()

    async def _check_endpoint_health(self) -> None:
        """Check API endpoint availability."""
        for endpoint in self.health_endpoints:
            url = f"{self.api_base_url}{endpoint}"
            success, status, response_time = await http_check(url)

            if success:
                self.logger.info(
                    f"Health check {endpoint}: OK ({status}) in {response_time:.2f}s"
                )
            else:
                if status == 0:
                    self.logger.error(f"Health check {endpoint}: UNREACHABLE")
                else:
                    self.logger.warning(
                        f"Health check {endpoint}: {status} in {response_time:.2f}s"
                    )

    async def _check_response_times(self) -> None:
        """Monitor API response times against SLO targets."""
        # SLO targets from docs/SLO.md
        slo_targets = {
            "/healthz": 0.1,  # 100ms
            "/api/v1/bookings": 0.5,  # 500ms
            "/api/v1/compliance": 2.0,  # 2s
        }

        for endpoint, target in slo_targets.items():
            url = f"{self.api_base_url}{endpoint}"
            _, status, response_time = await http_check(url)

            if status > 0 and response_time > target:
                self.logger.warning(
                    f"SLO violation: {endpoint} responded in {response_time:.2f}s "
                    f"(target: {target}s)"
                )


class DatabaseMonitorAgent(Agent):
    """Agent for monitoring database health and performance.

    Monitors:
    - Connection pool status
    - Migration status
    - Query performance metrics
    """

    async def execute(self) -> None:
        """Execute database monitoring tasks."""
        self.logger.info(f"Database monitor agent {self.config.name} checking database")

        await self._check_connection()
        await self._check_migrations()

    async def _check_connection(self) -> None:
        """Check database connection status."""
        database_url = os.getenv("DATABASE_URL", "")

        if not database_url:
            self.logger.warning(
                "DATABASE_URL not set - cannot check database connection"
            )
            return

        # Try to import and check database connection
        try:
            from prep.database import get_session_factory

            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute("SELECT 1")
                self.logger.info("Database connection: OK")
        except ImportError:
            self.logger.debug("prep.database not available - skipping connection check")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")

    async def _check_migrations(self) -> None:
        """Check migration status using alembic."""
        repo_root = Path.cwd()

        if not shutil.which("alembic"):
            self.logger.debug("alembic not installed - skipping migration check")
            return

        if not (repo_root / "alembic.ini").exists():
            self.logger.debug("No alembic.ini found - skipping migration check")
            return

        try:
            process = await asyncio.create_subprocess_exec(
                "alembic",
                "current",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_root,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            output = stdout.decode()
            if "head" in output.lower():
                self.logger.info("Database migrations: up to date")
            else:
                self.logger.warning(
                    f"Database migrations may be pending: {output[:200]}"
                )
        except asyncio.TimeoutError:
            self.logger.error("Migration check timed out")
        except Exception as e:
            self.logger.error(f"Migration check failed: {e}")


class BuildMonitorAgent(Agent):
    """Agent for monitoring build and CI/CD status.

    Monitors:
    - GitHub Actions workflow status
    - Build artifacts
    - Deployment status
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER", "")
        self.repo_name = os.getenv("GITHUB_REPO_NAME", "")

    async def execute(self) -> None:
        """Execute build monitoring tasks."""
        self.logger.info(f"Build monitor agent {self.config.name} checking builds")

        await self._check_workflow_health()
        await self._check_local_build()

    async def _check_workflow_health(self) -> None:
        """Check GitHub Actions workflow health."""
        if not all([self.github_token, self.repo_owner, self.repo_name]):
            self.logger.debug(
                "GitHub credentials not configured - skipping workflow check"
            )
            return

        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/actions/runs"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, params={"per_page": 10}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        runs = data.get("workflow_runs", [])

                        failed_runs = [
                            r for r in runs if r.get("conclusion") == "failure"
                        ]
                        if failed_runs:
                            self.logger.warning(
                                f"{len(failed_runs)}/10 recent workflow runs failed"
                            )
                            for run in failed_runs[:3]:
                                self.logger.warning(
                                    f"  {run.get('name')}: {run.get('conclusion')} - {run.get('html_url')}"
                                )
                        else:
                            self.logger.info("All recent workflow runs successful")
                    else:
                        self.logger.debug(f"GitHub API returned {resp.status}")
        except Exception as e:
            self.logger.debug(f"Could not check GitHub workflows: {e}")

    async def _check_local_build(self) -> None:
        """Check if local build artifacts are up to date."""
        repo_root = Path.cwd()

        # Check Python package build
        dist_dir = repo_root / "dist"
        if dist_dir.exists():
            wheel_files = list(dist_dir.glob("*.whl"))
            if wheel_files:
                newest = max(wheel_files, key=lambda p: p.stat().st_mtime)
                age = datetime.now().timestamp() - newest.stat().st_mtime
                age_hours = age / 3600

                if age_hours > 24:
                    self.logger.info(f"Build artifacts are {age_hours:.0f}h old")
                else:
                    self.logger.debug("Build artifacts are recent")


class PerformanceMonitorAgent(Agent):
    """Agent for monitoring application performance.

    Monitors:
    - System resource usage
    - Application metrics
    - Performance baselines
    """

    async def execute(self) -> None:
        """Execute performance monitoring tasks."""
        self.logger.info(
            f"Performance monitor agent {self.config.name} checking performance"
        )

        await self._check_resource_usage()
        await self._check_disk_usage()

    async def _check_resource_usage(self) -> None:
        """Monitor CPU, memory usage."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            if cpu_percent > 80:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
            else:
                self.logger.debug(f"CPU usage: {cpu_percent}%")

            if memory.percent > 85:
                self.logger.warning(f"High memory usage: {memory.percent}%")
            else:
                self.logger.debug(f"Memory usage: {memory.percent}%")

        except ImportError:
            self.logger.debug("psutil not installed - skipping resource check")

    async def _check_disk_usage(self) -> None:
        """Monitor disk usage."""
        try:
            import psutil

            disk = psutil.disk_usage("/")

            if disk.percent > 90:
                self.logger.error(f"Critical disk usage: {disk.percent}%")
            elif disk.percent > 80:
                self.logger.warning(f"High disk usage: {disk.percent}%")
            else:
                self.logger.debug(f"Disk usage: {disk.percent}%")

        except ImportError:
            self.logger.debug("psutil not installed - skipping disk check")


class RepositoryMonitorAgent(Agent):
    """General repository monitoring agent.

    Monitors:
    - Repository structure
    - Dependency freshness
    - Stale branches
    """

    async def execute(self) -> None:
        """Execute general repository monitoring tasks."""
        self.logger.info(
            f"Repository monitor agent {self.config.name} checking repository"
        )

        await self._check_dependencies_updates()
        await self._check_stale_branches()
        await self._check_file_structure()

    async def _check_dependencies_updates(self) -> None:
        """Check for outdated dependencies."""
        repo_root = Path.cwd()

        # Check Python dependencies
        if (repo_root / "requirements.txt").exists() and shutil.which("pip"):
            try:
                process = await asyncio.create_subprocess_exec(
                    "pip",
                    "list",
                    "--outdated",
                    "--format=json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60)

                outdated = json.loads(stdout.decode()) if stdout else []
                if outdated:
                    self.logger.info(
                        f"{len(outdated)} Python packages have updates available"
                    )
                    for pkg in outdated[:5]:
                        self.logger.debug(
                            f"  {pkg.get('name')}: {pkg.get('version')} -> {pkg.get('latest_version')}"
                        )
                else:
                    self.logger.info("All Python packages are up to date")
            except Exception as e:
                self.logger.debug(f"Could not check Python dependencies: {e}")

        # Check Node.js dependencies
        package_json = repo_root / "package.json"
        if package_json.exists() and shutil.which("npm"):
            try:
                process = await asyncio.create_subprocess_exec(
                    "npm",
                    "outdated",
                    "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=repo_root,
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60)

                outdated = json.loads(stdout.decode()) if stdout else {}
                if outdated:
                    self.logger.info(
                        f"{len(outdated)} npm packages have updates available"
                    )
            except Exception as e:
                self.logger.debug(f"Could not check npm dependencies: {e}")

    async def _check_stale_branches(self) -> None:
        """Check for stale git branches."""
        repo_root = Path.cwd()

        if not (repo_root / ".git").exists():
            self.logger.debug("Not a git repository - skipping branch check")
            return

        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname:short) %(committerdate:relative)",
                "refs/heads/",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_root,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)

            branches = stdout.decode().strip().split("\n") if stdout else []
            stale_keywords = ["months ago", "year ago", "years ago"]

            stale_branches = [
                b for b in branches if any(kw in b for kw in stale_keywords)
            ]

            if stale_branches:
                self.logger.info(
                    f"{len(stale_branches)} branches haven't been updated recently"
                )
                for branch in stale_branches[:5]:
                    self.logger.debug(f"  {branch}")
            else:
                self.logger.debug("No stale branches found")

        except Exception as e:
            self.logger.debug(f"Could not check branches: {e}")

    async def _check_file_structure(self) -> None:
        """Check repository file structure for common issues."""
        repo_root = Path.cwd()

        required_files = [
            "README.md",
            "LICENSE",
            ".gitignore",
            "requirements.txt",
        ]

        missing_files = [f for f in required_files if not (repo_root / f).exists()]

        if missing_files:
            self.logger.warning(
                f"Missing recommended files: {', '.join(missing_files)}"
            )
        else:
            self.logger.debug("All recommended files present")
