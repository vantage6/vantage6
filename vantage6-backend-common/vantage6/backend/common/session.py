# DB connection session. This is used by the iPython shell (from server import
# session). Flask requests obtain their session from `g.session` which is
# initialized on `pre_request`.
session = None
