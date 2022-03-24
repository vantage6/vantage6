from vantage6.server import create_app


server_app = create_app('/mnt/config.yaml', system_folders=False)
app = server_app.app
