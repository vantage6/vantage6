import os
import sys
import importlib
import inspect
import json
import traceback

from enum import Enum
from inspect import getmembers, isfunction, ismodule, signature
from pathlib import Path
from types import ModuleType

import click
import questionary as q
import pandas as pd

from vantage6.algorithm.client import AlgorithmClient
from vantage6.common import error, info

from pprint import pprint


class FunctionArgumentType(Enum):
    """Type of the function argument"""

    PARAMETER = "parameter"
    DATAFRAME = "dataframe"


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
@click.option(
    "--output-file",
    default="new-algorithm.json",
    type=str,
    help="Path to the output file",
)
# TODO note in the docstring that some algorithm json fields (e.g. ui_visualizations)
# are not supported. Or support filling them in manually.
# unsupported: ui_visualizations, databases, step_type, display_name
# unsupported for arguments: conditional_value, conditional_operator,
# type==column|organization|json|...
# TODO print warnings that the output should always be checked
# TODO create JSON file for infra functions so that those are always created
# correctly - these values should not be overwritten by the command unless flag
def cli_algorithm_generate_algorithm_json(
    algo_function_file: str, current_json: str, output_file: str
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

    # read the current algorithm.json file
    with open(current_json, "r", encoding="utf-8") as f:
        current_json_data = json.load(f)
        pprint(current_json_data)

    # get the functions from the file
    info(f"Importing functions from {algo_function_file}...")
    functions = _get_functions_from_file(algo_function_file)

    info("Converting functions to JSON...")
    function_json = _convert_functions_to_json(functions)

    # write the new algorithm.json file
    info(f"Writing new algorithm.json file to {output_file}...")
    current_json_data["functions"] = function_json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(current_json_data, f, indent=2)

    info(f"New algorithm.json file written to {output_file}")


def _convert_functions_to_json(functions: list) -> list:
    """Convert the functions to a JSON format"""
    function_jsons = []
    for func in functions:
        print(func)
        try:
            func_json = _read_function_signature(func)
        except Exception as e:
            traceback.print_exc()
            error(f"Error reading function signature for {func.__name__}: {e}")
            exit(1)

        pprint(func_json)
        # print(func_json)
        print()
        function_jsons.append(func_json)
    return function_jsons


def _read_function_signature(func: callable) -> dict:
    """Read the signature of the function"""
    sig = signature(func)
    # TODO steptype based on the decoration of the function
    function_json = {
        "name": func.__name__,
        "display_name": _pretty_print_name(func.__name__),
        "standalone": True,
        "description": _extract_headline_of_docstring(func.__doc__),
        "ui_visualizations": [],
        "arguments": [],
        "databases": [],
    }
    for name, param in sig.parameters.items():
        arg_json, arg_type = _get_argument_json(func, name, param)
        if arg_json is None:
            continue
        elif arg_type == FunctionArgumentType.DATAFRAME:
            function_json["databases"].append(arg_json)
        else:
            function_json["arguments"].append(arg_json)
    return function_json


def _pretty_print_name(name: str) -> str:
    """Pretty print the name of the function"""
    pretty = name.replace("_", " ")
    if len(pretty):
        pretty = pretty[0].upper() + pretty[1:]
    return pretty


def _extract_headline_of_docstring(docstring: str) -> str:
    """Extract the headline of the docstring"""
    if not docstring:
        return ""

    # Split by double newlines to get the first paragraph
    paragraphs = docstring.split("\n\n")
    first_paragraph = paragraphs[0]

    # Split by single newlines and join the lines with spaces
    lines = first_paragraph.split("\n")
    header = " ".join(line.strip() for line in lines if line.strip() != "")
    return header


def _get_argument_json(
    func: callable, name: str, param: inspect.Parameter
) -> tuple[dict | None, FunctionArgumentType | None]:
    """Get the argument JSON"""

    if param.annotation is None:
        error(f"Function {func.__name__} has no annotation for argument {name}")
        info(f"Please add a type annotation to the argument {name}")
        info(f"For example, for string arguments: 'def {func.__name__}({name}: str)'")
        exit(1)

    if param.annotation is AlgorithmClient:
        # Algorithm client arguments do not have to be provided by the user
        return None, None
    elif param.annotation is pd.DataFrame:
        # this is an argument that requires the user to supply a dataframe. That only
        # requires a name and description.
        return {
            "name": name,
            "description": _extract_parameter_description(name, func.__doc__),
        }, FunctionArgumentType.DATAFRAME
    else:
        # This is a regular function parameter
        # TODO add type (column|organization|json|...)
        arg_json = {
            "name": name,
            "display_name": _pretty_print_name(name),
            "description": _extract_parameter_description(name, func.__doc__),
            "type": str(param.annotation),
            "required": param.default == inspect.Parameter.empty,
            "has_default_value": param.default != inspect.Parameter.empty,
            "is_frontend_only": False,
            "conditional_value": None,
            "conditional_operator": None,
        }
        if param.default != inspect.Parameter.empty:
            arg_json["default"] = param.default
        return arg_json, FunctionArgumentType.PARAMETER


def _extract_parameter_description(name: str, docstring: str) -> str:
    """Extract the description of the parameter"""
    if not docstring:
        return ""

    # Try both patterns: "{name}:" and "{name} :"
    patterns = [f"{name}:", f"{name} :"]

    for pattern in patterns:
        if pattern in docstring:
            return docstring.split(pattern)[1].split("\n")[1].strip()

    return ""


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


def _get_algo_function_file_location(algo_function_file: str | None) -> None:
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
