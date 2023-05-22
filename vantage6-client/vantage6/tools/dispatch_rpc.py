import os
import importlib
import jwt
import traceback

from vantage6.client import ContainerClient
from vantage6.client.algorithm_client import AlgorithmClient
from vantage6.tools.util import info, warn, error


# TODO in v4+, set print_full_error to True, and remove use_new_client option
def dispatch_rpc(data, input_data, module, token, use_new_client=False,
                 print_full_error=False):

    # import algorithm module
    try:
        lib = importlib.import_module(module)
        info(f"Module '{module}' imported!")
    except ModuleNotFoundError:
        error(f"Module '{module}' can not be imported! Exiting...")
        exit(1)

    # in case of a master container, we have to do a little extra
    master = input_data.get("master")
    if master:
        info("Running a master-container")
        # read env
        host = os.environ["HOST"]
        port = os.environ["PORT"]
        api_path = os.environ["API_PATH"]

        # init Docker Client
        # TODO In v4+ we should always use the new client, delete option then
        if use_new_client:
            client = AlgorithmClient(token=token, host=host, port=port,
                                     path=api_path)
        else:
            client = ContainerClient(token=token, host=host, port=port,
                                     path=api_path)

        # read JWT token, to log te collaboration id. The
        # AlgorithmClient automatically sets the collaboration_id
        claims = jwt.decode(token, options={"verify_signature": False})

        # Backwards comptability from < 3.3.0
        if 'identity' in claims:
            id_ = claims['identity']['collaboration_id']
        elif 'sub' in claims:
            id_ = claims['sub']['collaboration_id']

        info(f"Working with collaboration_id <{id_}>")

        method_name = input_data["method"]

    else:
        info("Running a regular container")
        method_name = f"RPC_{input_data['method']}"

    # attempt to load the method
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
        error(f"Error encountered while calling {method_name}: {e}")
        if print_full_error:
            error(traceback.print_exc())
        exit(1)

    return result
