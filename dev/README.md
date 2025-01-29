# Development environment for vantage6

This directory contains files that can be aid in the development of vantage6 and
vantage6 algorithms.

~~It's meant to be cloned into the `dev` directory of the vantage6 repository.~~

> [!NOTE]
> As long as this code is not part of the offical vantage6 images and python cli
> tool, you need to adjust the following:
>
> Build the node-and-server image locally with:
> ```bash
> make TAG=devtestdebug REGISTRY=localhost:5050 PLATFORMS=linux/amd64 image
> ```
> This image should be referenced in the `docker-compose.yaml` for the server
> and the node yaml config file. There shouldn't be a need to push this image
> to a localhost:5050 registry.
>
> If you are using the `v6` cli tool for an algorithm development, you need to
> use this branch's version. You can do that by doing something like the
> following on your algorithm repository root:
> ```bash
> python3 -m venv venv
> source venv/bin/activate
> git clone -b devtestdebug https://github.com/vantage6/vantage6.git venv/vantage6
> cd /this/branch/checked/out/venv/vantage6
> make install-cli-dev
> ```
> For vscode to play nice, you may need:
> ```json
> {
>     "python.analysis.extraPaths": [
>         "/this/branch/checked/out/vantage6/vantage6",
>         "/this/branch/checked/out/vantage6/vantage6-algorithm-tools",
>         "/this/branch/checked/out/vantage6/vantage6-algorithm-store",
>         "/this/branch/checked/out/vantage6/vantage6-backend-common",
>         "/this/branch/checked/out/vantage6/vantage6-client",
>         "/this/branch/checked/out/vantage6/vantage6-common",
>         "/this/branch/checked/out/vantage6/vantage6-node",
>         "/this/branch/checked/out/vantage6/vantage6-server"
>     ],
> }
>

### Debugging vantage6 code

Our setup here uses debugpy. While in theory this will work with any client that
implements the [Debugger Adapter
Protocol](https://microsoft.github.io/debug-adapter-protocol/), we've only
tested it with Visual Studio Code and config files for it are provided.

When we want to debug the code of a vantage6 component (e.g. the server, a node,
etc) we launch the component in a way that allows a debugger to attach to it
before it starts executing. This is done via `debugpy`.  For example, for the
node, its entrypoint (container) is modified to run `debugpy` which will wait
for a debugger (e.g. vscode) to connect to it.  Scripts like `node-debug.sh` for
the node and `server-debug.sh` are the entrypoints that must be chosen for this
to happen. They reside in the `/vantage6/dev/debugger/` directory (vantage6
repository) and are volumed mapped into the component's container.

Normally `/vantage6/vantage6-node/node.sh` and
`/vantage6/vantage6-server/server.sh` (again, vantage6 repository) are the
entrypoints for the node and server respectively. But when the following
configuration is found in the config yaml for the node or the server, this
entrypoint is modified accordingly:

```yaml
debugger:
  # directory on the host where debugpy module and `node-debug.sh` live
  dir: ../../../debugger
  cmd: ./node-debug.sh
  # host IP to bind to
  host: 127.0.6.10
  # host port to bind to
  port_host: 5678
  # container port the above host:port_host is mapped to
  port_container: 5678
```

Note that relative paths are relative to where the config file is located. In
the future I believe we should leverage docker compose for most of these things
(e.g. volume mapping, port mapping, etc). But at the moment we rely on the `v6
node start` script for setting up the volumes, network, etc necessary for the
node to run.

If we reach the point where we can easily define server and *node* in a
docker-compose, this whole `v6 dev profiles` tooling will be fairly unnecessary,
as would be most `v6` commands.


#### Manual procedure (without `v6 dev profile`)

So, you could create a node and add something like the configuration excerpt
above to it. And make sure it can connect to whatever server you configued too.
You would then run `v6 node start` and the node conatiner would be waiting for a
debugger client to attach to it. You can create a configuration in vscode's
`launch.json` like this:
```json
{
    "name": "Debug: Node",
    "type": "debugpy",
    "request": "attach",
    "connect": {
        "host": "127.0.6.10",
        "port": 5678
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/vantage6"
        }
    ],
    // Starts debug node in a task and *waits for you* to control-C
    // the task before debugger attaches.
    "preLaunchTask": "start debug node",
},
```
And a task in `tasks.json` like this:
```json
{
    "label": "start debug node",
    "type": "shell",
    "command": "${workspaceFolder}/dev/venv/bin/v6",
    "args": [
        "node", "start",
        "--mount-src", "${workspaceFolder}",
        "--config", "path/to/your/config.yaml",
        "--attach"
    ],
    "presentation": {
        "reveal": "always"
    },
    "group": "none",
},
```

You can then run the `Debug: Node` configuration in vscode (Control+Shift+D) and
the container node (via debugpy) will start and wait for you to Control-C the
task that launched it before the debugger (vscode) attaches.

Then it will stop at whatever breakpoint you have set in the code as long as you
trigger that code path.

*This is cumbersome*, however. So that's why we have the `v6 dev profile` and
*provide many of these files already (node configs, server configs, launch.json,
*tasks.json, etc).


#### Using `v6 dev profile`

We provide different sets of configurations (profiles) made up of a bunch of
files (node configs, launch.json, tasks.json, docker-compose.yaml, etc). At the
moment, only the profiles bundle "planets" exists.

All these files are meant to be used in conjuction with the `v6 dev profile`
command. This command accepts a `profiles.json` file specifying the different
configurations to stand up (e.g. 1 server and 2 nodes or just the server or 1
server, 1 node meant for debugging and one other node running normally). Each of
these configuartions we call a profile. One profile might tailor to an algorithm
developer, another to a developer working on server code, etc.

A few files that are generally involved:
* `profiles.json`: Expected by `v6 dev profile`. Specifies the different
  combinations of server and nodes to
  run. For example, a profile for someone making changes to the node code might be
  one in which the server is running normally (no debugging) and the a node is run
  in a way that allows debugging (e.g. waiting for vscode's debugger to attach to
  the v6 node running via debugpy).
* `launch.json`: Specifies different configurations for debugging. Debug the
  planets server, the planets mars node, etc.
* `tasks.json`: Specifies different tasks that can be run. They are used by the
different configuration in `launch.json`. For example, starting the a task can
starst the planets server and the planets mars node in debugging mode. This is
proving more cumbersome than I thought. Probably not worth it.
* `config.yaml`: Each server or node uses a configuration file in vantage6. For
  example, the planets server, or the planets mars node.

Because developers might want to use different sets of configurations (e.g.
planets-macos, algorithm-maker, etc), all these file bundles could be kept in a
separate directory (e.g. `dev/v6-developers/`, `dev/algorithm-developers`, etc).

You can create symbolic links from your vantage6's `.vscode` directory to the
corresponding profile's vscode directory. This way, you can easily switch
between different configurations.

For example:

```bash
git clone git@github.com:vantage6/vantage6.git
cd vantage6
mkdir -p .vscode
ln -s ../dev/v6-dev-profile/vscode/tasks.json tasks.json
ln -s ../dev/v6-dev-profile/vscode/launch.json launch.json
```

#### Using `v6 dev profile` to start the planets profile

In `./dev/v6-dev-profile/profiles.json` different profiles are defined. For example:
```json
        "run-node-mars": {
            "server": {
                "compose": "server/docker-compose.yaml",
                "service": "server-planets-dev"
            },
            "ui": {
                "compose": "server/docker-compose.yaml",
                "service": "ui-planets"
            },
            "nodes": [
                {
                    "name": "mars",
                    "config": "nodes/mars/mars.yaml",
                    "options": {
                        "skip_debugger": true,
                        "attach": true
                    }
                }
            ]
        },
```

To start it, you can run:
```
v6 dev profile --profiles ./dev/v6-dev-profile/profiles.json start run-node-mars
```


### Networking details
The profile `planets` uses the following IP addresses:
- `127.0.6.1`: Server Planets
- `127.0.6.10`: Node Mars
- `127.0.6.11`: Node Jupiter
- `127.0.6.12`: Node Saturn
- `127.0.66.10`: Algorithms spawned by Mars
- `127.0.66.11`: Algorithms spawned by Jupiter
- `127.0.66.12`: Algorithms spawned by Saturn
- `127.0.0.6`: `launch.json`'s "Attach to local debugpy (v6)". You can start

All this addresses are loopback addresses, so they are only accessible from the
local machine. They map to localhost. In fact any IP in the range 127.0.0.0/8 is
a loopback address as defined in [RFC
3330](https://tools.ietf.org/html/rfc3330).

You can ask Docker to bind to a specific IP address and port and have the
executable inside the container (e.g. vantage6-server) get that traffic. For
example, [from the documetation of
Docker](https://docs.docker.com/engine/network/)
> `-p 192.168.1.100:8080:80` Map port 8080 on the Docker host IP 192.168.1.100
> to TCP port 80 in the container.

This can allow you to use the same port on the host for different containers.
You can ask the server it's version `curl http://127.0.6.1/api/version` or
attach to its debugger using 127.0.6.1:5678. While at the same time, attach to
the one of the nodes' debugpy using 127.0.6.10:5678. There is no need to open a
service at the host level by binding to 0.0.0.0. Besides this, modifications
have been made to the node start script (`v6 node start`) to be able to have the
node and server communicate to each other using an internal docker created
network.

However, while Linux seems to incorporate the entire range (127.0.0.0/8), MacOS
only seems to incorporate the ip 127.0.0.1. To achive the same effect on MacOS,
you can use the following commands:
```bash
for lo_ip in 127.0.6.1 127.0.6.10 127.0.6.11 127.0.6.12 127.0.66.10 127.0.66.11 127.0.66.12; do
    sudo ifconfig lo0 alias $lo_ip up
done
```
See [this
post](https://superuser.com/questions/458875/how-do-you-get-loopback-addresses-other-than-127-0-0-1-to-work-on-os-x
) for reference.

### Debugging `v6` cli tool
In Linux you can something like this to your shell.
```
debugpy_run () {
        if [ "$#" -lt 1 ]
        then
                echo "Usage: debugpy_run <command>"
                return 1
        fi
        python -Xfrozen_modules=off -m debugpy --listen 127.0.0.6:5678 --wait-for-client "$@"
}
```
And then you can run something like `debugpy_run =v6 start node` (zsh) or
``debugpy_run `which v6` start node`` (bash). This will wait until you connect
to the debugger, which you can do by running the `Attach to local debugpy (v6)`
configuration in vscode. Here's what that configuration looks like:
```json
{
    "name": "Attach to local debugpy (v6)",
    "type": "debugpy",
    "request": "attach",
    "connect": {
        "host": "127.0.0.6",
        "port": 5678
    },
    "justMyCode": false
},
```

### Algorithm development environment

##### Debugging

You can add to a node's configuartion file something like this:
```yaml
debugger_algorithm:
  # dir containing debugger (e.g. debugpy for python) and starting script
  # (entrypoint)
  debug_dir: ../../debugger
  # command to execute as entrypoint (working dir will be debug_dir)
  launcher: ./algorithm-debug-python.sh
  # top of the algorithm source directory
  algo_source_dir: ../../../..
  # source will be mounted on /app on the container
  algo_dest_dir: /app
  # host to bind to (docker)
  host: 127.0.66.10
  # host port to bind to
  port_host: 5678
  # internal port
  port_container: 5678
```

This will start any algorithm spawned by this node using the
`algorithm-debug-python.sh` script. Depeding on your algorithm, this script
might change. The basic idea is that will run what would be the regular
entrypoint of your algorithm via a debugger. In python, this could be debugpy.

Once you send a task, the logs from the algorithm container will be outputted to
the node logs. That way you can watch out for when you should attach your
client debugger to the debugger running the algorithm code within the container.

The `debug_dir` is a directory that should contain your debugger (i.e.  an
executable that is able to run the code an interact with a client to set
breakpoints, etc). It may also contain the entrypoint script.

The `algo_source_dir` and `algo_dest_dir` are paths to the algorithm source (on
your host) and the path on the container where this algorihtm source code should
be mounted to.

Note that when using the algorithm debugger, algorithms will have network
connectivity, as we need it for the developer to connect to the algorithm
continaer to communicated with the debugger running the code.

### Running algorithms locally

:construction: TODO :construction:

You can also simply use the `v6 dev profile` to start up a whole environment
while being able to easily edit the config files. This can come in handy in your
algorithm depends on node-side configuration settings via environment variables
for example. The goal is to make it very easy to stand up a whole environment to
the point that using the mock client is not necessary. And have it be an
environment that is virtually the same as a the "real" one.

In planets, you can use the "`run-all-planets`" to start the server three
nodes without debugging mode.
