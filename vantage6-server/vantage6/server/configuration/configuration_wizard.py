

# TODO deprecated, still used by server instance, should be replaced
# by some sort of questionaire
def get_config_location(ctx, config, force_create):
    """Ensure configuration file exists and return its location."""
    return config if config else ctx.config_file
