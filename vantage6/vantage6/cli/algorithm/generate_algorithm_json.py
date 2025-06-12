import os
import sys
import importlib
from pathlib import Path
from inspect import getmembers, isfunction, getmodule

import click
import questionary as q


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
def cli_algorithm_generate_algorithm_json(
    algo_function_file: str, current_json: str
) -> dict:
    """
    Generate an updated algorithm.json file to submit to the algorithm store.

    You should provide the path to the file where the algorithm functions are
    defined.
    """
    algo_function_file = _get_algo_function_file_location(algo_function_file)
    print(algo_function_file)

    current_json = _get_current_json_location(current_json)
    print(current_json)

    # get the functions from the file
    functions = _get_functions_from_file(algo_function_file)
    print(functions)


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
    print(package_name, module_name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Could not import module {module_name}: {str(e)}")

    # Get all functions from the module, including imported ones
    funcs = []
    for name, func in getmembers(module, isfunction):
        # Skip private functions
        if name.startswith("_"):
            continue

        funcs.append(func)

    return funcs


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
