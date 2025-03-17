# from pathlib import Path
# import click

# from vantage6.common.globals import Ports
# from vantage6.cli.utils import info
# from vantage6.cli.dev.create import create_demo_network
# from vantage6.cli.dev.start import start_demo_network
# from vantage6.cli.dev.stop import stop_demo_network
# from vantage6.cli.dev.remove import remove_demo_network
# from vantage6.cli.utils import prompt_config_name, check_config_name_allowed
# from vantage6.cli.test.feature_tester import cli_test_features


# @click.command()
# @click.option(
#     "-n", "--name", default=None, type=str, help="Name for your development setup"
# )
# @click.option(
#     "--server-url",
#     type=str,
#     default="http://host.docker.internal",
#     help="Server URL to point to. If you are using Docker Desktop, "
#     "the default http://host.docker.internal should not be changed.",
# )
# @click.option(
#     "-i", "--image", type=str, default=None, help="Server Docker image to use"
# )
# @click.option(
#     "--keep",
#     type=bool,
#     default=False,
#     help="Keep the dev network after finishing the test",
# )
# @click.option(
#     "--extra-server-config",
#     type=click.Path(exists=True),
#     default=None,
#     help="YAML File with additional server "
#     "configuration. This will be appended to the server "
#     "configuration file",
# )
# @click.option(
#     "--extra-node-config",
#     type=click.Path("rb"),
#     default=None,
#     help="YAML File with additional node configuration. This will be"
#     " appended to each of the node configuration files",
# )
# @click.pass_context
# def cli_test_integration(
#     click_ctx: click.Context,
#     name: str,
#     server_url: str,
#     image: str,
#     keep: bool = False,
#     extra_server_config: Path = None,
#     extra_node_config: Path = None,
# ) -> list[dict]:
#     """
#     Create dev network and run diagnostic checks on it.

#     This is a full integration test of the vantage6 network. It will create
#     a test server with some nodes using the `vdev` commands, and then run the
#     v6-diagnostics algorithm to test all functionality.
#     """
#     # get name for the development setup - if not given - and check if it is
#     # allowed
#     name = prompt_config_name(name)
#     check_config_name_allowed(name)

#     # create server & node configurations and create test resources (
#     # collaborations, organizations, etc)
#     click_ctx.invoke(
#         create_demo_network,
#         name=name,
#         num_nodes=3,
#         server_url=server_url,
#         server_port=Ports.DEV_SERVER.value,
#         image=image,
#         extra_server_config=extra_server_config,
#         extra_node_config=extra_node_config,
#     )

#     # start the server and nodes
#     click_ctx.invoke(
#         start_demo_network,
#         name=name,
#         server_image=image,
#         node_image=image,
#     )

#     # run the diagnostic tests
#     # TODO the username and password should be coordinated with the vdev
#     # command - at present it spits out this username/password combination by
#     # default but both should be defined in the same place
#     # TODO VPN testing is always excluded - allow to include it with a flag
#     # when vdev commands can handle extra config parameters
#     diagnose_results = click_ctx.invoke(
#         cli_test_features,
#         host="http://localhost",
#         port=Ports.DEV_SERVER.value,
#         api_path="/api",
#         username="dev_admin",
#         password="password",
#         collaboration=1,
#         organizations=None,
#         all_nodes=True,
#         online_only=False,
#         no_vpn=True,
#     )

#     # clean up the test resources
#     click_ctx.invoke(stop_demo_network, name=name)
#     if not keep:
#         click_ctx.invoke(remove_demo_network, name=name)
#     else:
#         info(
#             f"Keeping the demo network {name}. You can start it with `v6 dev "
#             "start-demo-network`"
#         )

#     return diagnose_results
