import click

from pathlib import Path
from vantage6.dev.profiles import ProfileManager


@click.group()
@click.option(
    "--profiles",
    type=click.Path(exists=True),
    help="Path to profiles.json. If not provided, will search in ./dev/v6-dev-profile/profiles.json and ./tests/v6-dev-profile/profiles.json.",
)
@click.pass_context
def profile(click_ctx, profiles):
    """Manage profiles with start/stop subcommands."""
    default_paths = [
        # default vantage6 development profile
        Path("./dev/v6-dev-profile/profiles.json"),
        # usual path for v6 algorithm development
        Path("./tests/v6-dev-profile/profiles.json"),
    ]

    if not profiles:
        profiles = next((path for path in default_paths if path.exists()), None)
        if profiles:
            click.echo(f"Using default profiles.json: {profiles}")
        else:
            raise click.UsageError(
                f"Could not find {', '.join(str(p) for p in default_paths)}.\n"
                "Please provide a path to profiles.json with --profiles"
            )

    click_ctx.ensure_object(dict)
    click_ctx.obj["manager"] = ProfileManager(profiles)


@profile.command()
@click.pass_context
def list(click_ctx):
    """List all available profiles."""
    manager = click_ctx.obj["manager"]
    profiles = manager.list_profiles()
    click.echo("Available profiles:")
    for profile in profiles:
        click.echo(f" - {profile}")


@profile.command()
@click.argument("profile_name", metavar="<PROFILE>")
@click.pass_context
def start(click_ctx, profile_name):
    """Start a specific profile."""
    manager = click_ctx.obj["manager"]
    profile = manager.get_profile(profile_name)
    profile.start()


@profile.command()
@click.argument("profile_name", metavar="<PROFILE>")
@click.pass_context
def stop(click_ctx, profile_name):
    """Stop a specific profile."""
    manager = click_ctx.obj["manager"]
    profile = manager.get_profile(profile_name)
    profile.stop()
