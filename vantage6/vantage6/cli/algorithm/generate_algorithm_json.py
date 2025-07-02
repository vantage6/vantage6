import os
import sys
import importlib
import inspect
import json
import traceback

from enum import Enum
from inspect import getmembers, isfunction, ismodule, signature
from pathlib import Path
from types import ModuleType, UnionType

import click
import questionary as q
import pandas as pd

from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.tools import DecoratorType
from vantage6.common import error, info, warning
from vantage6.common.enum import AlgorithmArgumentType, AlgorithmStepType
from vantage6.algorithm.preprocessing.algorithm_json_data import (
    PREPROCESSING_FUNCTIONS_JSON_DATA,
)


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

    # get the functions from the file
    info(f"Importing functions from {algo_function_file}...")
    functions = _get_functions_from_file(algo_function_file)

    info("Converting functions to JSON...")
    function_json = _convert_functions_to_json(functions)

    # merge the function jsons with the json data from the algorithm_json_data module
    function_json = _merge_function_jsons_with_json_data(function_json, functions)

    # write the new algorithm.json file
    info(f"Writing new algorithm.json file to {output_file}...")
    # TODO don't overwrite the current json file, but merge it with the new one - e.g.
    # the old one may already have descriptions etc that should not be overwritten
    current_json_data["functions"] = function_json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(current_json_data, f, indent=2)

    info(f"New algorithm.json file written to {output_file}")

    warning(
        "Always check the generated algorithm.json file before submitting it to the "
        "algorithm store!"
    )


def _merge_function_jsons_with_json_data(function_jsons: list, functions: list) -> list:
    """
    Merge the function jsons with the json data from the algorithm_json_data module
    """
    for function_json in function_jsons:
        # Only merge the function jsons with template json data if it is an
        # infrastructure-defined function
        func_callable = next(
            f for f in functions if f.__name__ == function_json["name"]
        )
        if (
            not func_callable
            or not func_callable.__module__.startswith("vantage6.algorithm.")
            or not function_json["name"] in PREPROCESSING_FUNCTIONS_JSON_DATA
        ):
            continue

        # get the template json data for the function
        template_json = PREPROCESSING_FUNCTIONS_JSON_DATA[function_json["name"]]
        # merge the dicts, with the template dict taking precedence
        for argument in function_json["arguments"]:
            if argument["name"] in template_json["arguments"]:
                argument.update(template_json["arguments"][argument["name"]])
        # Add any frontend arguments specified in the template json
        if "frontend_arguments" in template_json:
            for frontend_argument in template_json["frontend_arguments"]:
                _add_frontend_argument(function_json, template_json, frontend_argument)

    return function_jsons


def _add_frontend_argument(
    function_json: dict, template_json: dict, frontend_argument: str
) -> None:
    """Add a frontend argument to the function json"""
    frontend_argument_json: dict = template_json["frontend_arguments"][
        frontend_argument
    ]
    before_arg_name = frontend_argument_json.pop("before_argument")

    try:
        before_arg_idx = next(
            idx
            for idx, arg in enumerate(function_json["arguments"])
            if arg["name"] == before_arg_name
        )
        function_json["arguments"].insert(before_arg_idx, frontend_argument_json)
    except StopIteration:
        warning(
            f"Could not find argument {before_arg_name} in function "
            f"{function_json['name']}. Frontend argument {frontend_argument} "
            "will not be added."
        )


def _convert_functions_to_json(functions: list) -> list:
    """Convert the functions to a JSON format"""
    function_jsons = []
    for func in functions:
        try:
            func_json = _read_function_signature(func)
        except Exception as e:
            traceback.print_exc()
            error(f"Error reading function signature for {func.__name__}: {e}")
            exit(1)

        function_jsons.append(func_json)
    return function_jsons


def _read_function_signature(func: callable) -> dict:
    """Read the signature of the function"""
    sig = signature(func)
    function_json = {
        "name": func.__name__,
        "display_name": _pretty_print_name(func.__name__),
        "standalone": True,
        "description": _extract_headline_of_docstring(func.__doc__),
        "step_type": _get_step_type(func),
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
            "name": name if name != "df" else "Data to use",
            "description": _extract_parameter_description(name, func.__doc__),
        }, FunctionArgumentType.DATAFRAME
    else:
        # This is a regular function parameter
        # TODO add type (column|organization|json|...)
        arg_json = {
            "name": name,
            "display_name": _pretty_print_name(name),
            "description": _extract_parameter_description(name, func.__doc__),
            "type": _get_argument_type(param, name, func),
            "required": param.default == inspect.Parameter.empty,
            "has_default_value": param.default != inspect.Parameter.empty,
            "is_frontend_only": False,
        }
        if param.default != inspect.Parameter.empty:
            arg_json["default"] = param.default
        return arg_json, FunctionArgumentType.PARAMETER


def _get_argument_type(param: inspect.Parameter, name: str, func: callable) -> str:
    """Get the type of the argument"""

    if type(param.annotation) is UnionType:
        # Arguments with default values may have type 'str | None'. If that is the case,
        # we want to use the type of the first element in the union.
        if len(param.annotation.__args__) > 2:
            # if there are more than 2 elements in the union, we don't know what to do
            warning(
                f"Unsupported argument type: {param.annotation} for argument {name} "
                f"in function {func.__name__}"
            )
            return None
        elif len(param.annotation.__args__) == 2:
            # if there are two, we want to use the first one if the second is None
            if param.annotation.__args__[1] is type(None):
                type_ = param.annotation.__args__[0]
            else:
                warning(
                    f"Unsupported argument type: {param.annotation} for argument {name}"
                    f" in function {func.__name__}"
                )
                return None
        else:
            # normally, unions have 2+ elements. If there is only one, we can use that
            type_ = param.annotation.__args__[0]

    else:
        type_ = param.annotation

    if type_ == str:
        return AlgorithmArgumentType.STRING.value
    elif type_ == dict:
        return AlgorithmArgumentType.JSON.value
    elif type_ == int:
        return AlgorithmArgumentType.INTEGER.value
    elif type_ == float:
        return AlgorithmArgumentType.FLOAT.value
    elif type_ == bool:
        return AlgorithmArgumentType.BOOLEAN.value
    elif type_ == list:
        return AlgorithmArgumentType.STRINGS.value
    elif type_ == list[str]:
        return AlgorithmArgumentType.STRINGS.value
    elif type_ == list[int]:
        return AlgorithmArgumentType.INTEGERS.value
    elif type_ == list[float]:
        return AlgorithmArgumentType.FLOATS.value
    else:
        warning(
            f"Unsupported argument type: {param.annotation} for argument {name} "
            f"in function {func.__name__}"
        )
        return None


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
            [
                m
                for m in second_level_import_members
                if isfunction(m) and _is_decorated_func(m)
            ]
        )

    return import_functions


def _is_decorated_func(func: callable) -> bool:
    """Check if the function is decorated with a vantage6 decorator, which all
    functions being called in vantage6 algorithm should be"""
    return _get_vantage6_decorator_type(func) is not None


def _get_vantage6_decorator_type(func: callable) -> str:
    """Get the vantage6 decorator type of the function"""
    return getattr(func, "vantage6_decorated_type", None)


def _get_step_type(func: callable) -> str:
    """Get the step type of the function"""
    decorator_type = _get_vantage6_decorator_type(func)
    if decorator_type == DecoratorType.FEDERATED:
        return AlgorithmStepType.FEDERATED_COMPUTE.value
    elif decorator_type == DecoratorType.CENTRAL:
        return AlgorithmStepType.CENTRAL_COMPUTE.value
    elif decorator_type == DecoratorType.PREPROCESSING:
        return AlgorithmStepType.PREPROCESSING.value
    elif decorator_type == DecoratorType.DATA_EXTRACTION:
        return AlgorithmStepType.DATA_EXTRACTION.value
    else:
        warning(
            f"Unsupported decorator type: {decorator_type} for function {func.__name__}"
        )
        return None


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
