import os
import sys
import importlib
import traceback
from pathlib import Path
from inspect import getmembers, isfunction, ismodule, signature
import inspect
from types import ModuleType

import click
import questionary as q

from vantage6.algorithm.client import AlgorithmClient
from vantage6.common import error, info


@click.command()
@click.option(
    "--algo-function-file",
    default=None,
    type=str,
    help="Path to the file containing or importing the algorithm functions",
)
@click.option(
    "--current-json",
    default=None,
    type=str,
    help="Path to the current algorithm.json file",
)
# TODO note in the docstring that some algorithm json fields (e.g. ui_visualizations)
# are not supported. Or support filling them in manually.
# unsupported: ui_visualizations, databases, step_type, display_name
# unsupported for arguments: description, conditional_value, conditional_operator,
# display_name, type==column|organization|json|...
def cli_algorithm_generate_algorithm_json(
    algo_function_file: str, current_json: str
) -> dict:
    """
    Generate an updated algorithm.json file to submit to the algorithm store.

    You should provide the path to the file where the algorithm functions are
    defined.

    Note that if you do asterisk ('from x import *') imports, all functions from the
    imported module will be added to the algorithm.json file.
    """
    algo_function_file = _get_algo_function_file_location(algo_function_file)

    current_json = _get_current_json_location(current_json)

    # get the functions from the file
    functions = _get_functions_from_file(algo_function_file)

    function_json = _convert_functions_to_json(functions)


def _convert_functions_to_json(functions: list) -> list:
    """Convert the functions to a JSON format"""
    for func in functions:
        print(func)
        try:
            func_json = _read_function_signature(func)
        except Exception as e:
            traceback.print_exc()
            error(f"Error reading function signature for {func.__name__}: {e}")
            exit(1)
        print(func_json)
        print()


def _read_function_signature(func: callable) -> dict:
    """Read the signature of the function"""
    sig = signature(func)
    # TODO steptype based on the decoration of the function
    # TODO also databases
    return {
        "name": func.__name__,
        "standalone": True,
        "description": func.__doc__,
        "ui_visualizations": [],
        "arguments": [
            arg_json
            for name, param in sig.parameters.items()
            if (arg_json := _get_argument_json(func, name, param)) is not None
        ],
    }


def _get_argument_json(
    func: callable, name: str, param: inspect.Parameter
) -> dict | None:
    """Get the argument JSON"""

    if param.annotation is None:
        error(f"Function {func.__name__} has no annotation for argument {name}")
        info(f"Please add a type annotation to the argument {name}")
        info(f"For example, for string arguments: 'def {func.__name__}({name}: str)'")
        exit(1)

    if param.annotation is AlgorithmClient:
        return None  # Algorithm client arguments do not have to be provided by the user

    return {
        "name": name,
        # "description": param.description,
        "type": param.annotation,
        "required": param.default == inspect.Parameter.empty,
        "default": param.default if param.default != inspect.Parameter.empty else None,
        "is_frontend_only": False,
    }


def _get_functions_from_file(file_path: str) -> None:
    """Get the functions from the file

    Parameters
    ----------
    file_path : str
        Path to the file containing or importing the algorithm functions
    """
    # Convert path to absolute path
    file_path = str(Path(file_path).resolve())

    # Get the package root directory (two levels up from the file)
    package_root = str(Path(file_path).parent.parent)
    if package_root not in sys.path:
        sys.path.insert(0, package_root)

    # Get the module name from the file path, including the package name
    package_name = Path(file_path).parent.name
    module_name = f"{package_name}.{Path(file_path).stem}"

    # Import the module
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Could not import module {module_name}: {str(e)}")

    def get_members_from_module(module: ModuleType) -> list:
        """Get the functions from the module"""
        return [
            member for name, member in getmembers(module) if not name.startswith("_")
        ]

    # get the functions from the algorithm module
    import_members = get_members_from_module(module)
    import_functions = [m for m in import_members if isfunction(m)]
    import_modules = [m for m in import_members if ismodule(m)]

    # add the functions from the imported modules (only 1 level deep). This is so that
    # if you do e.g. 'from vantage6.algorithm.preprocessing import *', all functions
    # from within those modules are also imported.
    for import_module in import_modules:
        second_level_import_members = get_members_from_module(import_module)
        import_functions.extend(
            [m for m in second_level_import_members if isfunction(m)]
        )

    return import_functions


def _get_algo_function_file_location(algo_function_file: str) -> None:
    """Get user input for the algorithm creation

    Parameters
    ----------
    algo_function_file : str
        Path to the file containing or importingthe algorithm functions
    """
    if not algo_function_file:
        default_dir = str(Path(os.getcwd()) / "__init__.py")
        algo_function_file = q.text(
            "Path to the file containing or importing the algorithm functions:",
            default=default_dir,
        ).unsafe_ask()

    # Convert to absolute path using pathlib
    algo_function_file = str(Path(algo_function_file).resolve())

    # check if the file exists
    if not Path(algo_function_file).exists():
        raise FileNotFoundError(f"File {algo_function_file} does not exist")

    return algo_function_file


def _get_current_json_location(current_json: str) -> None:
    """Get user input for the current algorithm.json file

    Parameters
    ----------
    current_json : str
        Path to the current algorithm.json file
    """
    if not current_json:
        default_dir = str(Path(os.getcwd()) / "algorithm_store.json")
        current_json = q.text(
            "Path to the current algorithm.json file:",
            default=default_dir,
        ).unsafe_ask()

    # Convert to absolute path using pathlib
    current_json = str(Path(current_json).resolve())

    # check if the file exists
    if not Path(current_json).exists():
        raise FileNotFoundError(f"File {current_json} does not exist")

    return current_json
