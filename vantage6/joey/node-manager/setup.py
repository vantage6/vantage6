from setuptools import setup, find_packages

setup(
    name="nodemanager",
    version="0.0-dev",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "dockermanager=nodemanager:start_container"
        ]
    }
)