import os
import importlib
import jwt

from vantage6.client import ContainerClient
from vantage6.tools.util import info, warn


def dispact_rpc(data, input_data, module, token):

    # import algorithm module
    try:
        lib = importlib.import_module(module)
        info(f"Module '{module}' imported!")
    except ModuleNotFoundError:
        warn(f"Module '{module}' can not be imported!")

    # in case of a master container, we have to do a little extra
    master = input_data.get("master")
    if master:
        info("Running a master-container")
        # read env
        host = os.environ["HOST"]
        port = os.environ["PORT"]
        api_path = os.environ["API_PATH"]

        # init Docker Client
        client = ContainerClient(token=token, host=host, port=port,
                                 path=api_path)

        # read JWT token, to log te collaboration id. The
        # ContainerClient automatically sets the collaboration_id

        claims = jwt.decode(token, verify=False)
        id_ = claims["identity"]["collaboration_id"]
        info(f"Working with collaboration_id <{id_}>")

        method_name = input_data["method"]

    else:
        info("Running a regular container")
        method_name = f"RPC_{input_data['method']}"

    # attemt to load the method
    try:
        method = getattr(lib, method_name)
    except AttributeError:
        warn(f"method '{method_name}' not found!\n")
        exit(1)

    # get the args and kwargs input for this function.
    args = input_data.get("args", [])
    kwargs = input_data.get("kwargs", {})

    # try to run the method
    try:
        result = method(client, data, *args, **kwargs) if master else \
                 method(data, *args, **kwargs)
    except Exception as e:
        warn(f"Error encountered while calling {method_name}: {e}")
        exit(1)

    return result
