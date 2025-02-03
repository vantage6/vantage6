"""
**PoC**: ideally replaced by docker compose files. We'll see if the concept is
useful and if so what do we refactor. Clearly plenty to refactor below!

Allows for loading different predefined (profiles.json) vantage6 networks. For
example a server with two nodes, one of the nodes ready for debugging.

This is useful for node and server development purposes, where you want to
stand up a vantage6 network, make modifications to the configuration files of
the server and node, change the dataset, etc.

It can also be used to develop algorithms, using a profile that does not make
use of a debugger for server and node but that does use debugger for the
algorithm.

And finally, for tests. In which as an algorithm developer you want to stand up
a predefined vantage6 network and run your algorithm on it in different ways
for testing purposes.

Note: Ideally this would be completely replaced by simply using docker compose
files where servers and nodes are specified. But alas, it is not possible at
the moment to start up a node using docker compose alone.
"""

import json
import logging
import subprocess
from pathlib import Path

from vantage6.cli.node.start import cli_node_start
from vantage6.cli.node.stop import cli_node_stop
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

class ProfileManager:
    """Manages vantage6 dev profiles."""

    def __init__(self, profiles_path):
        self.profiles_path = Path(profiles_path).resolve()
        self._profiles_data = self._load_profiles_json()
        self.settings = self._profiles_data.get("settings", {})

    def _load_profiles_json(self):
        """Loads and validates, and processes profiles from the JSON file."""
        try:
            with open(self.profiles_path, "r") as f:
                profiles_json = json.load(f)

            base_path = self.profiles_path.parent
            for profile in profiles_json["profiles"].values():
                profile["server"]["compose"] = self._process_path(
                    profile, ("server", "compose"), base_path
                )
                profile["ui"]["compose"] = self._process_path(
                    profile, ("ui", "compose"), base_path
                )
                for node in profile.get("nodes", []):
                    node["config"] = self._process_path(node, ("config",), base_path)

            if "mount_src_path" in profiles_json.get("settings", {}):
                mount_src = self._process_path(
                    profiles_json, ("settings", "mount_src_path"), base_path
                )
                self._validate_mount_src(mount_src)
                profiles_json["settings"]["mount_src_path"] = mount_src

            return profiles_json
        except Exception as e:
            raise RuntimeError(f"Error loading profiles: {e}")

    def _validate_mount_src(self, mount_src):
        """Minimally validates (poorly) that mount_src path looks like a
        vantage6 development tree."""
        required_dirs = ["vantage6-node", "vantage6-server", "vantage6-client"]
        if not all(Path(mount_src, req_dir).exists() for req_dir in required_dirs):
            raise FileNotFoundError(
                f"Path {mount_src} for mount_src does not look like a vantage6 tree. "
                f"Required directories: {', '.join(required_dirs)}"
            )

    def _process_path(self, config_dict, property, base_path):
        """Converts relative paths to absolute paths and validates them."""
        target = config_dict
        for p in property:
            if p in target:
                target = target[p]
            else:
                return None

        if isinstance(target, str):
            target = Path(target)
            if not target.is_absolute():
                target = base_path / target

        if not target.exists():
            raise FileNotFoundError(f"Path {target} does not exist.")
        return str(target)

    def get_profile(self, profile_name):
        """Retrieve a profile by name."""
        profiles = self._profiles_data.get("profiles", {})
        if profile_name not in profiles:
            raise ValueError(f"Profile '{profile_name}' not found.")
        return Profile(profile_name, profiles[profile_name], self.settings)

    def list_profiles(self):
        """List all available profiles."""
        return list(self._profiles_data.get("profiles", {}).keys())


class Profile:
    """Represents a single vantage6 dev profile."""

    def __init__(self, name, profile_data, settings):
        self.name = name
        self.profile_data = profile_data
        self.settings = settings

    def start(self):
        # server first, nodes depend on it
        if "server" in self.profile_data:
            self._start_service(
                self.profile_data["server"]["compose"],
                self.profile_data["server"]["service"],
            )
        if "ui" in self.profile_data:
            self._start_service(
                self.profile_data["ui"]["compose"], self.profile_data["ui"]["service"]
            )
        if "nodes" in self.profile_data:
            for node in self.profile_data["nodes"]:
                self._start_node(node)

    def stop(self):
        if "ui" in self.profile_data:
            self._stop_service(
                self.profile_data["ui"]["compose"], self.profile_data["ui"]["service"]
            )
        if "nodes" in self.profile_data:
            for node in self.profile_data["nodes"]:
                self._stop_node(node)

        # server last, potential dev network defined in server's docker-compose
        if "server" in self.profile_data:
            self._stop_service(
                self.profile_data["server"]["compose"],
                self.profile_data["server"]["service"],
            )

    def _start_service(self, compose_file, service):
        log.debug("Starting service: %s with %s", service, compose_file)
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "up", "-d", service], check=True
        )

    def _stop_service(self, compose_file, service):
        log.debug("Stopping service: %s with %s", service, compose_file)
        # this is dev/tests, hence `-t 1` to speed up the shutdown
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "down", service, "-t", "1"],
            check=True
        )

    def _start_node(self, node):
        """Starts a node using cli"""
        options = node.get("options", {})
        args = ["--config", node["config"]]

        if options.get("skip_debugger", False):
            args.append("--no-debugger")

        if options.get("attach", False):
            args.append("--attach")

        if self.settings.get("mount_src_path") and not options.get("skip_mount_src", False):
            args.extend(["--mount-src", self.settings["mount_src_path"]])

        log.debug("Starting node: %s with config %s", node["name"], node["config"])
        cli_node_start(args, standalone_mode=False)


    def _stop_node(self, node):
        """Stops a node using cli"""
        log.debug("Stopping node: %s with config %s", node['name'], node['config'])
        cli_node_stop(["--config", node["config"]], standalone_mode=False)

