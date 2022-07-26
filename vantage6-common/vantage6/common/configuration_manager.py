import yaml
import collections

from pathlib import Path
from schema import Schema


class Configuration(collections.UserDict):
    """Base to contains a single configuration."""

    VALIDATORS = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        """ Validation of a single item when put
        """
        # assert key in self.VALIDATORS.keys(), "Invalid Key!"
        schema = Schema(
            self.VALIDATORS.get(key, lambda x: True),
            ignore_extra_keys=True
        )
        assert schema.is_valid(value), \
            f"Invalid value '{value}' provided for field '{key}'"
        super().__setitem__(key, value)

    def __getitem__(self, key):
        if key in self.data:
            return super().__getitem__(key)
        else:
            raise KeyError(key)

    @property
    def is_valid(self):
        schema = Schema(self.VALIDATORS, ignore_extra_keys=True)
        return schema.is_valid(self.data)


class ConfigurationManager(object):
    """Class to maintain valid configuration settings.

    A configuration file contains at top level an `application` and/or
    `environments` key. The `environments` key can contain up to four
    keys: `dev`, `test`, `acc`, `prod`. e.g.:
    application:
        ...
    environments:
        dev:
            ...
        test:
            ...
        acc:
            ...
        prod:
            ...

    Note that this structure is the same for the node and server.
    """
    ENVS = ("application", "prod", "acc", "test", "dev")

    def __init__(self, conf_class=Configuration, name=None):
        self.application = ""
        self.prod = ""
        self.acc = ""
        self.test = ""
        self.dev = ""

        self.name = name
        self.conf_class = conf_class

    def put(self, env: str, config: dict):
        assert env in self.ENVS
        configuration = self.conf_class(config)
        # only set valid configs
        if configuration.is_valid:
            self.__setattr__(env, configuration)
        # else:
        #      print(f"config={config}")
        #      print(self.conf_class)

    def get(self, env: str):
        assert env in self.ENVS
        return self.__getattribute__(env)

    @property
    def is_empty(self):
        return not (self.application or self.prod or self.acc
                    or self.test or self.dev)

    @property
    def environments(self):
        return {"prod": self.prod, "acc": self.acc, "test": self.test,
                "dev": self.dev, "application": self.application}

    @property
    def has_application(self):
        return bool(self.application)

    @property
    def has_environments(self):
        return any([bool(env) for key, env in self.environments])

    @property
    def available_environments(self):
        return [key for key, env in self.environments.items() if env]

    def _get_environment_from_dict(self, d, e):
        assert e in self.ENVS
        if e == "application":
            return d.get("application", {})
        else:
            return d.get("environments", {}).get(e, {})

    def load(self, path):
        with open(str(path), 'r') as f:
            config = yaml.safe_load(f)

        for env in self.ENVS:
            self.put(env, self._get_environment_from_dict(config, env))

    @classmethod
    def from_file(cls, path, conf_class=Configuration):
        name = Path(path).stem
        assert name, f"Name could not be extracted from filepath={path}"
        conf = cls(name=name, conf_class=conf_class)
        conf.load(path)
        return conf

    def save(self, path):

        config = {"application": dict(self.application), "environments": {
            "prod": dict(self.prod),
            "acc": dict(self.acc),
            "test": dict(self.test),
            "dev": dict(self.dev)}
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
