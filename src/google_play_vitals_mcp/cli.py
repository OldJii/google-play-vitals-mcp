"""
CLI Entry Point for Google Play Vitals MCP Server
Supports running stdio server, self-diagnostics check, and version inquiry.
"""

import json

import click

from . import __version__
from .server import GooglePlayVitalsMCPServer


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version and exit.",
)
@click.option(
    "--package-name",
    "-p",
    type=str,
    default=None,
    help="Default Android package name (e.g., com.example.app).",
)
@click.option(
    "--credentials",
    "-c",
    type=click.Path(exists=False),
    default=None,
    help="Path to GCP Service Account JSON key.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    version: bool,
    package_name: str | None,
    credentials: str | None,
) -> None:
    """Google Play Vitals MCP Server - LLM-Optimized Quality & Performance Suite."""
    if version:
        click.echo(f"google-play-vitals-mcp version {__version__}")
        ctx.exit(0)

    ctx.ensure_object(dict)
    ctx.obj["package_name"] = package_name
    ctx.obj["credentials"] = credentials

    if ctx.invoked_subcommand is None:
        # Default action: run MCP stdio server
        server = GooglePlayVitalsMCPServer(
            default_package_name=package_name,
            default_credentials_path=credentials,
        )
        server.run_stdio()


@cli.command("run")
@click.pass_context
def run_command(ctx: click.Context) -> None:
    """Start the Model Context Protocol (MCP) server in stdio mode."""
    pkg = ctx.obj.get("package_name")
    cred = ctx.obj.get("credentials")
    server = GooglePlayVitalsMCPServer(
        default_package_name=pkg,
        default_credentials_path=cred,
    )
    server.run_stdio()


@cli.command("check")
@click.pass_context
def check_command(ctx: click.Context) -> None:
    """Run diagnostics to verify Python dependencies and Google Cloud credentials."""
    pkg = ctx.obj.get("package_name")
    cred = ctx.obj.get("credentials")
    server = GooglePlayVitalsMCPServer(
        default_package_name=pkg,
        default_credentials_path=cred,
    )
    result = server.handle_check_status(
        {
            "package_name": pkg,
            "credentials_path": cred,
        }
    )
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cli()
