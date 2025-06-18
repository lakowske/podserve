"""Command line interface for PodServe."""

import click


@click.command()
@click.version_option()
def main() -> None:
    """PodServe CLI."""
    click.echo("PodServe CLI - Container-based pod server")


if __name__ == "__main__":
    main()
