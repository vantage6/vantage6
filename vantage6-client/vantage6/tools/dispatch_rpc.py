import importlib

from types import ModuleType
from typing import Any

from vantage6.tools.util import info, warn, error


def dispatch_rpc(input_data: dict, module: ModuleType) -> Any:
    """
    Load the algorithm module and call the correct method to run an algorithm.

    Parameters
    ----------
    input_data : dict
        The input data that is passed to the algorithm. This should at least
        contain the key 'method' which is the name of the method that should be
        called. Another often used key is 'master' which indicates that this
        container is a master container. Other keys depend on the algorithm.
    module : ModuleType
        The module that contains the algorithm.

    Returns
    -------
    Any
        The result of the algorithm.
    """
    # import algorithm module
    try:
        lib = importlib.import_module(module)
        info(f"Module '{module}' imported!")
    except ModuleNotFoundError:
        error(f"Module '{module}' can not be imported! Exiting...")
        exit(1)

    # in case of a master container, we have to do a little extra
    method_name = input_data["method"]

    # attempt to load the method
    try:
        method = getattr(lib, method_name)
    except AttributeError:
        warn(f"Method '{method_name}' not found!\n")
        exit(1)

    # get the args and kwargs input for this function.
    args = input_data.get("args", [])
    kwargs = input_data.get("kwargs", {})

    # try to run the method
    try:
        result = method(*args, **kwargs)
    except Exception as e:
        warn(f"Error encountered while calling {method_name}: {e}")
        exit(1)

    return result
