- yaml instead of json for profiles(.json)
- keep track of which profile have been started (or which containers from what
  profile have been started), so they can be removed
- v6 dev profile restart
- update https://github.com/mdw-nl/v6-average-py/pull/1 (@lsago working on this)
  to match new pytest fixtures integrated into v6
- refactor dev profile
  - perhaps take v6 node start code out of clicker, so it can be used nicely in dev profile (no subcommand)
  - keep in mind ultimate goal would be to use docker-compose for node and server, so calibrate effort
- remove skip_debugger option
  - not worth extra complexity. Either just don't do --wait-for-client, or have
    two different node config yamls with debug/no-debug
