import importlib
import inspect
import json
import os
import sys
from inspect import getmembers, isfunction, ismodule, signature
from pathlib import Path
from types import ModuleType, UnionType
from typing import Any, OrderedDict

import click
import pandas as pd
import questionary as q

from vantage6.common import error, info, warning
from vantage6.common.algorithm_function import (
    get_vantage6_decorator_type,
    is_vantage6_algorithm_func,
)
from vantage6.common.enum import AlgorithmArgumentType, AlgorithmStepType, StrEnumBase

from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.preprocessing.algorithm_json_data import (
    PREPROCESSING_FUNCTIONS_JSON_DATA,
)


class MergePreference:
    """Singleton class to manage global merge preference state"""

    _instance = None
    _prefer_existing = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MergePreference, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_preference(cls) -> bool | None:
        """Get the current merge preference"""
        return cls._prefer_existing

    @classmethod
    def set_preference(cls, prefer_existing: bool) -> None:
        """Set the merge preference globally"""
        cls._prefer_existing = prefer_existing

    @classmethod
    def reset(cls) -> None:
        """Reset the preference to None"""
        cls._prefer_existing = None


class FunctionArgumentType(StrEnumBase):
    """Type of the function argument"""

    PARAMETER = "parameter"
    DATAFRAME = "dataframe"


class Function:
    """Class to handle a function and its JSON representation"""

    def __init__(self, func: callable):
        self.func = func
        self.name = func.__name__
        self.signature = signature(func)
        self.docstring = func.__doc__
        self.json = None
        self.step_type = None

    def prepare_json(self) -> None:
        """Convert the function to a JSON format"""
        self.step_type = self._get_step_type()
        function_json = {
            "name": self.name,
            "display_name": self._pretty_print_name(self.name),
            "standalone": True,
            "description": self._extract_headline_of_docstring(),
            "step_type": self.step_type.value if self.step_type else None,
            "ui_visualizations": [],
            "arguments": [],
            "databases": [],
        }

        parameters = OrderedDict(self.signature.parameters)

        # if the function is a data extraction function, the first argument is a dict
        # with database connection details. This argument should not be added to the
        # function json. Instead, a database should be added to the function json.
        if self.step_type == AlgorithmStepType.DATA_EXTRACTION:
            function_json["databases"].append(
                {
                    "name": "Database",
                    "description": "Database to extract data from",
                }
            )
            # remove database connection details from the signature
            parameters.popitem(last=False)

        # add the arguments to the function json
        for name, param in parameters.items():
            arg_json, arg_type = self._get_argument_json(name, param)
            if arg_json is None:
                continue
            elif arg_type == FunctionArgumentType.DATAFRAME:
                function_json["databases"].append(arg_json)
            else:
                function_json["arguments"].append(arg_json)
        self.json = function_json

    def merge_with_template_json_data(self) -> None:
        """
        Merge the function jsons with the json data from the algorithm_json_data module
        """
        # Only merge the function jsons with template json data if it is an
        # infrastructure-defined function
        if (
            not self.func.__module__.startswith("vantage6.algorithm.")
            or self.json["name"] not in PREPROCESSING_FUNCTIONS_JSON_DATA
        ):
            return

        # get the template json data for the function
        template_json = PREPROCESSING_FUNCTIONS_JSON_DATA[self.json["name"]]
        # merge the dicts, with the template dict taking precedence
        for argument in self.json["arguments"]:
            if argument["name"] in template_json["arguments"]:
                argument.update(template_json["arguments"][argument["name"]])
        # Add any frontend arguments specified in the template json
        if "frontend_arguments" in template_json:
            for frontend_argument in template_json["frontend_arguments"]:
                self._add_frontend_argument(template_json, frontend_argument)

    def merge_with_existing_json(self, existing_json: dict) -> None:
        """Merge the function json with the existing json data"""
        self._merge_dicts(self.json, existing_json)

    def _merge_dicts(self, target: dict, source: dict) -> None:
        """
        Recursively merge source dict into target dict, with source taking precedence
        """
        for key, value in source.items():
            if key in target:
                if isinstance(value, dict) and isinstance(target[key], dict):
                    # Recursively merge nested dictionaries
                    self._merge_dicts(target[key], value)
                else:
                    self._replace_target_with_source(target, key, value)
            else:
                # Add new key-value pair from source to target
                self._replace_target_with_source(target, key, value)

    def _replace_target_with_source(self, target: dict, key: str, value: Any) -> None:
        """Replace the value in target with the one from source"""
        if target[key] == value:
            return

        prefer_existing = MergePreference.get_preference()
        if prefer_existing:
            target[key] = value
        elif prefer_existing is None:
            info(
                f"Different values for the same key '{key}' in function '{self.name}' "
                "were found."
            )
            info(f"Value from function itself: {target[key]}")
            info(f"Value from algorithm.json: {value}")
            result = q.select(
                "Please select the value to keep:",
                choices=[
                    "function itself",
                    "algorithm.json",
                    "function itself (also for all other conflicts)",
                    "algorithm.json (also for all other conflicts)",
                ],
            ).unsafe_ask()
            if result == "algorithm.json":
                target[key] = value
            elif result == "function itself":
                pass  # do nothing
            elif result == "function itself (also for all other conflicts)":
                MergePreference.set_preference(False)
            elif result == "algorithm.json (also for all other conflicts)":
                MergePreference.set_preference(True)
                target[key] = value

    def _get_argument_json(
        self, name: str, param: inspect.Parameter
    ) -> tuple[dict | None, FunctionArgumentType | None]:
        """Get the argument JSON"""

        if param.annotation is None:
            error(f"Function {self.name} has no annotation for argument {name}")
            info(f"Please add a type annotation to the argument {name}")
            info(f"For example, for string arguments: 'def {self.name}({name}: str)'")
            exit(1)

        if param.annotation is AlgorithmClient:
            # Algorithm client arguments do not have to be provided by the user
            return None, None
        elif param.annotation is pd.DataFrame:
            # this is an argument that requires the user to supply a dataframe. That
            # only requires a name and description.
            return {
                "name": name if name != "df" else "Data to use",
                "description": self._extract_parameter_description(name),
            }, FunctionArgumentType.DATAFRAME
        else:
            # This is a regular function parameter
            type_ = self._get_argument_type(param, name)
            arg_json = {
                "name": name,
                "display_name": self._pretty_print_name(name),
                "description": self._extract_parameter_description(name),
                "type": type_.value if type_ else None,
                "required": param.default == inspect.Parameter.empty,
                "has_default_value": param.default != inspect.Parameter.empty,
                "is_frontend_only": False,
            }
            if param.default != inspect.Parameter.empty:
                arg_json["default"] = param.default
            return arg_json, FunctionArgumentType.PARAMETER

    def _add_frontend_argument(
        self, template_json: dict, frontend_argument: str
    ) -> None:
        """Add a frontend argument to the function json"""
        frontend_argument_json: dict = template_json["frontend_arguments"][
            frontend_argument
        ]
        before_arg_name = frontend_argument_json.pop("before_argument")

        try:
            before_arg_idx = next(
                idx
                for idx, arg in enumerate(self.json["arguments"])
                if arg["name"] == before_arg_name
            )
            self.json["arguments"].insert(before_arg_idx, frontend_argument_json)
        except StopIteration:
            warning(
                f"Could not find argument {before_arg_name} in function "
                f"{self.json['name']}. Frontend argument {frontend_argument} "
                "will not be added."
            )

    def _get_argument_type(
        self, param: inspect.Parameter, name: str
    ) -> AlgorithmArgumentType | None:
        """Get the type of the argument"""
        if isinstance(param.annotation, UnionType):
            # Arguments with default values may have type 'str | None'. If that is the
            # case, we want to use the type of the first element in the union.
            if len(param.annotation.__args__) > 2:
                # if there are more than 2 elements in the union, don't handle
                warning(
                    f"Unsupported argument type: {param.annotation} for argument {name}"
                    f" in function {self.name}"
                )
                return None
            elif len(param.annotation.__args__) == 2:
                # if there are two, we want to use the first one if the second is None
                if param.annotation.__args__[1] is type(None):
                    type_ = param.annotation.__args__[0]
                else:
                    warning(
                        f"Unsupported argument type: {param.annotation} for argument "
                        f"{name} in function {self.name}"
                    )
                    return None
            else:
                # normally, unions have 2+ elements. If there is only one, use that
                type_ = param.annotation.__args__[0]
        else:
            type_ = param.annotation

        if type_ == str:
            return AlgorithmArgumentType.STRING
        elif type_ == dict:
            return AlgorithmArgumentType.JSON
        elif type_ == int:
            return AlgorithmArgumentType.INTEGER
        elif type_ == float:
            return AlgorithmArgumentType.FLOAT
        elif type_ == bool:
            return AlgorithmArgumentType.BOOLEAN
        elif type_ == list:
            return AlgorithmArgumentType.STRINGS
        elif type_ == list[str]:
            return AlgorithmArgumentType.STRINGS
        elif type_ == list[int]:
            return AlgorithmArgumentType.INTEGERS
        elif type_ == list[float]:
            return AlgorithmArgumentType.FLOATS
        else:
            warning(
                f"Unsupported argument type: {param.annotation} for argument {name} "
                f"in function {self.name}"
            )
            return None

    def _pretty_print_name(self, name: str) -> str:
        """Pretty print the name of the function"""
        pretty = name.replace("_", " ")
        if len(pretty):
            pretty = pretty[0].upper() + pretty[1:]
        return pretty

    def _extract_headline_of_docstring(self) -> str:
        """Extract the headline of the docstring"""
        if not self.docstring:
            return ""

        # Split by double newlines to get the first paragraph
        paragraphs = self.docstring.split("\n\n")
        first_paragraph = paragraphs[0]

        # Split by single newlines and join the lines with spaces
        lines = first_paragraph.split("\n")
        header = " ".join(line.strip() for line in lines if line.strip() != "")
        return header

    def _get_step_type(self) -> AlgorithmStepType | None:
        """Get the step type of the function"""
        decorator_type = get_vantage6_decorator_type(self.func)
        if decorator_type in AlgorithmStepType.list():
            return decorator_type
        else:
            warning(
                f"Unsupported decorator type: {decorator_type} for function {self.name}"
            )
            return None

    def _extract_parameter_description(self, name: str) -> str:
        """Extract the description of the parameter"""
        if not self.docstring:
            return ""

        # Try both patterns: "{name}:" and "{name} :"
        patterns = [f"{name}:", f"{name} :"]

        for pattern in patterns:
            if pattern in self.docstring:
                return self.docstring.split(pattern)[1].split("\n")[1].strip()

        return ""


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
    function_objs = [Function(f) for f in functions]

    info("Converting functions to JSON...")
    for function in function_objs:
        function.prepare_json()
        function.merge_with_template_json_data()

        # merge the function jsons with the existing json data
        current_json_func = [
            f for f in current_json_data["functions"] if f["name"] == function.name
        ]
        if current_json_func:
            function.merge_with_existing_json(current_json_func[0])

    # write the new algorithm.json file
    info(f"Writing new algorithm.json file to {output_file}...")
    current_json_data["functions"] = [f.json for f in function_objs]
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(current_json_data, f, indent=2)

    info(f"New algorithm.json file written to {output_file}")

    warning("-" * 80)
    warning("Always check the generated algorithm.json file before submitting it to ")
    warning("the algorithm store!")
    warning("-" * 80)


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
        raise ImportError(f"Could not import module {module_name}: {str(e)}") from e

    def get_members_from_module(module: ModuleType) -> list:
        """Get the functions from the module"""
        return [
            member for name, member in getmembers(module) if not name.startswith("_")
        ]

    # get the functions from the algorithm module
    import_members = get_members_from_module(module)
    import_functions = [
        m for m in import_members if isfunction(m) and is_vantage6_algorithm_func(m)
    ]
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
                if isfunction(m) and is_vantage6_algorithm_func(m)
            ]
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
