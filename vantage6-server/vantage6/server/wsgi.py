from vantage6.server import create_app


app = create_app('/mnt/config.yaml', system_folders=False)
