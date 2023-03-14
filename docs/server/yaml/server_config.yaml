application: {}
  # you may also add your configuration here and leave environments empty

environments:
  # name of the environment (should be 'test', 'prod', 'acc' or 'dev')
  test:

    # Human readable description of the server instance. This is to help
    # your peers to identify the server
    description: Test

    # Should be prod, acc, test or dev. In case the type is set to test
    # the JWT-tokens expiration is set to 1 day (default is 6 hours). The
    # other types can be used in future releases of vantage6
    type: test

    # IP adress to which the server binds. In case you specify 0.0.0.0
    # the server listens on all interfaces
    ip: 0.0.0.0

    # Port to which the server binds
    port: 5000

    # API path prefix. (i.e. https://yourdomain.org/api_path/<endpoint>). In the
    # case you use a referse proxy and use a subpath, make sure to include it
    # here also.
    api_path: /api

    # The URI to the server database. This should be a valid SQLAlchemy URI,
    # e.g. for an Sqlite database: sqlite:///database-name.sqlite,
    # or Postgres: postgresql://username:password@172.17.0.1/database).
    uri: sqlite:///test.sqlite

    # This should be set to false in production as this allows to completely
    # wipe the database in a single command. Useful to set to true when
    # testing/developing.
    allow_drop_all: True

    # The secret key used to generate JWT authorization tokens. This should
    # be kept secret as others are able to generate access tokens if they
    # know this secret. This parameter is optional. In case it is not
    # provided in the configuration it is generated each time the server
    # starts. Thereby invalidating all previous distributed keys.
    # OPTIONAL
    jwt_secret_key: super-secret-key! # recommended but optional

    # Settings for the logger
    logging:

      # Controls the logging output level. Could be one of the following
      # levels: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
      level:        DEBUG

      # Filename of the log-file, used by RotatingFileHandler
      file:         test.log

      # Whether the output is shown in the console or not
      use_console:  True

      # The number of log files that are kept, used by RotatingFileHandler
      backup_count: 5

      # Size in kB of a single log file, used by RotatingFileHandler
      max_size:     1024

      # format: input for logging.Formatter,
      format:       "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s"
      datefmt:      "%Y-%m-%d %H:%M:%S"

    # Configure a smtp mail server for the server to use for administrative
    # purposes. e.g. allowing users to reset their password.
    # OPTIONAL
    smtp:
      port: 587
      server: smtp.yourmailserver.com
      username: your-username
      password: super-secret-password

    # Set an email address you want to direct your users to for support
    # (defaults to the address you set above in the SMTP server or otherwise
    # to support@vantage6.ai)
    support_email: your-support@email.com

    # set how long reset token provided via email are valid (default 1 hour)
    email_token_validity_minutes: 60

    # set how long tokens and refresh tokens are valid (default 6 and 48
    # hours, respectively)
    token_expires_hours: 6
    refresh_token_expires_hours: 48

    # If algorithm containers need direct communication between each other
    # the server also requires a VPN server. (!) This must be a EduVPN
    # instance as vantage6 makes use of their API (!)
    # OPTIONAL
    vpn_server:
        # the URL of your VPN server
        url: https://your-vpn-server.ext

        # OATH2 settings, make sure these are the same as in the
        # configuration file of your EduVPN instance
        redirect_url: http://localhost
        client_id: your_VPN_client_user_name
        client_secret: your_VPN_client_user_password

        # Username and password to acccess the EduVPN portal
        portal_username: your_eduvpn_portal_user_name
        portal_userpass: your_eduvpn_portal_user_password

  prod: {}
  acc: {}
  dev: {}