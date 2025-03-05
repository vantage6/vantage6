"""Python client for user to communicate with the vantage6 server"""

from __future__ import annotations

import logging
import time
from typing import List
import jwt
import pyfiglet
import itertools
import sys
import traceback

from pathlib import Path

from vantage6.common.globals import APPNAME, AuthStatus
from vantage6.common.encryption import DummyCryptor, RSACryptor
from vantage6.common import WhoAmI
from vantage6.common.serialization import serialize
from vantage6.common.client.utils import print_qr_code
from vantage6.common.enum import RunStatus
from vantage6.common.client.client_base import ClientBase
from vantage6.client.filter import post_filtering
from vantage6.client.utils import LogLevel
from vantage6.client.subclients.study import StudySubClient
from vantage6.client.subclients.store.algorithm import AlgorithmSubClient
from vantage6.client.subclients.store.algorithm_store import AlgorithmStoreSubClient
from vantage6.client.subclients.session import SessionSubClient
from vantage6.client.subclients.dataframe import DataFrameSubClient

# make sure the version is available
from vantage6.client._version import __version__  # noqa: F401


module_name = __name__.split(".")[1]


class UserClient(ClientBase):
    """User interface to the vantage6-server"""

    def __init__(self, *args, log_level="info", **kwargs) -> None:
        """Create user client

        All paramters from `ClientBase` can be used here.

        Parameters
        ----------
        log_level : str, optional
            The log level to use, by default 'info'
        """
        super(UserClient, self).__init__(*args, **kwargs)

        # Replace logger by print logger
        self.log = self._get_logger(log_level)

        # attach sub-clients
        self.util = self.Util(self)
        self.collaboration = self.Collaboration(self)
        self.organization = self.Organization(self)
        self.user = self.User(self)
        self.run = self.Run(self)
        self.result = self.Result(self)
        self.task = self.Task(self)
        self.role = self.Role(self)
        self.node = self.Node(self)
        self.rule = self.Rule(self)
        self.study = StudySubClient(self)
        self.store = AlgorithmStoreSubClient(self)
        self.algorithm = AlgorithmSubClient(self)
        self.session = SessionSubClient(self)
        self.dataframe = DataFrameSubClient(self)

        self.collaboration_id = None
        self.session_id = None

        # Display welcome message
        self.log.info(" Welcome to")
        for line in pyfiglet.figlet_format(APPNAME, font="big").split("\n"):
            self.log.info(line)
        self.log.info(" --> Join us on Discord! https://discord.gg/rwRvwyK")
        self.log.info(" --> Docs: https://docs.vantage6.ai")
        self.log.info(" --> Blog: https://vantage6.ai")
        self.log.info("-" * 60)
        self.log.info("Cite us!")
        self.log.info("If you publish your findings obtained using vantage6, ")
        self.log.info("please cite the proper sources as mentioned in:")
        self.log.info("https://vantage6.ai/vantage6/references")
        self.log.info("-" * 60)

    @staticmethod
    def _get_logger(level: str) -> logging.Logger:
        """
        Create print-logger

        Parameters
        ----------
        level: str
            Desired logging level

        Returns
        -------
        logging.Logger
            Logger object
        """
        # get logger that prints to console
        logger = logging.getLogger()
        logger.handlers.clear()
        logger.addHandler(logging.StreamHandler(sys.stdout))

        # set log level
        level = level.upper()
        if level not in [lvl.value for lvl in LogLevel]:
            default_lvl = LogLevel.DEBUG.value
            logger.setLevel(default_lvl)
            logger.warn(
                f"You set unknown log level {level}. Available levels are: "
                f"{', '.join([lvl.value for lvl in LogLevel])}. "
            )
            logger.warn(f"Log level now set to {default_lvl}.")
        else:
            logger.setLevel(level)
        return logger

    def authenticate(
        self, username: str, password: str, mfa_code: int | str = None
    ) -> None:
        """Authenticate as a user

        It also collects some additional info about your user.

        Parameters
        ----------
        username : str
            Username used to authenticate
        password : str
            Password used to authenticate
        mfa_code: str | int
            Six-digit two-factor authentication code
        """
        auth_json = {
            "username": username,
            "password": password,
        }
        if mfa_code:
            auth_json["mfa_code"] = mfa_code
        auth = super(UserClient, self).authenticate(auth_json, path="token/user")
        if not auth:
            # user is not authenticated. The super function is responsible for
            # printing useful output
            return

        # identify the user and the organization to which this user
        # belongs. This is usefull for some client side checks
        try:
            type_ = "user"
            id_ = jwt.decode(self.token, options={"verify_signature": False})["sub"]

            user = self.request(f"user/{id_}")
            name = user.get("firstname")
            organization_id = user.get("organization").get("id")
            organization = self.request(f"organization/{organization_id}")
            organization_name = organization.get("name")

            self.whoami = WhoAmI(
                type_=type_,
                id_=id_,
                name=name,
                organization_id=organization_id,
                organization_name=organization_name,
            )

            self.log.info(" --> Succesfully authenticated")
            self.log.info(f" --> Name: {name} (id={id_})")
            self.log.info(
                f" --> Organization: {organization_name} " f"(id={organization_id})"
            )

            # setup default encryption so user doesn't have to do this unless encryption
            # is enabled
            self.cryptor = DummyCryptor()
        except Exception:
            self.log.info("--> Retrieving additional user info failed!")
            self.log.error(traceback.format_exc())

    def setup_collaboration(self, collaboration_id: int) -> None:
        """Setup the collaboration.

        This gets the collaboration from the server and stores its details in
        the client and sets the algorithm stores available for this collaboration.
        When this has been called, other functions no longer require
        the `collaboration_id` to be provided.

        Parameters
        ----------
        collaboration_id : int
            Id of the collaboration
        """
        self.collaboration_id = collaboration_id
        self.log.info("Setting up collaboration %s", collaboration_id)
        response = self.request(f"collaboration/{collaboration_id}")
        if "msg" in response:
            self.log.info("--> %s", response["msg"])
            return

    def wait_for_results(self, task_id: int, interval: float = 1) -> dict:
        """
        Polls the server to check when results are ready, and returns the
        results when the task is completed.

        Parameters
        ----------
        task_id: int
            ID of the task that you are waiting for
        interval: float
            Interval in seconds between checks if task is finished. Default 1.

        Returns
        -------
        dict
            A dictionary with the results of the task, after it has completed.
        """
        # Disable logging (additional logging would prevent the 'wait' message
        # from being printed on a single line)
        prev_level = self.log.level
        self.log.setLevel(logging.WARN)

        animation = itertools.cycle(["|", "/", "-", "\\"])
        t = time.time()

        while not RunStatus.has_finished(self.task.get(task_id).get("status")):
            frame = next(animation)
            sys.stdout.write(
                f"\r{frame} Waiting for task {task_id} ({int(time.time()-t)}s)"
            )
            sys.stdout.flush()
            time.sleep(interval)
        sys.stdout.write("\rDone!                  ")

        # Re-enable logging
        self.log.setLevel(prev_level)

        result = self.request("result", params={"task_id": task_id})
        result = self.result._decrypt_result(result, is_single_result=False)
        return result

    class Util(ClientBase.SubClient):
        """Collection of general utilities"""

        def _get_server_url_header(self) -> dict:
            """
            Get the server url for request header to algorithm store

            Returns
            -------
            dict
                The server url in a dictionary so it can be used as header
            """
            return {"server_url": self.parent.base_path}

        def get_server_version(self, attempts_on_timeout: int = None) -> dict:
            """View the version number of the vantage6-server
            Parameters
            ----------
            attempts_on_timeout : int
                Number of attempts to make when the server is not responding.
                Default is unlimited.
            Returns
            -------
            dict
                A dict containing the version number
            """
            return self.parent.request(
                "version", attempts_on_timeout=attempts_on_timeout
            )

        def get_server_health(self) -> dict:
            """View the health of the vantage6-server

            Returns
            -------
            dict
                Containing the server health information
            """
            return self.parent.request("health")

        def change_my_password(self, current_password: str, new_password: str) -> dict:
            """Change your own password by providing your current password

            Parameters
            ----------
            current_password : str
                Your current password
            new_password : str
                Your new password

            Returns
            -------
            dict
                Message from the server
            """
            result = self.parent.request(
                "password/change",
                method="patch",
                json={
                    "current_password": current_password,
                    "new_password": new_password,
                },
            )
            msg = result.get("msg")
            self.parent.log.info(f"--> {msg}")
            return result

        def reset_my_password(self, email: str = None, username: str = None) -> dict:
            """Start reset password procedure

            Either a username of email needs to be provided.

            Parameters
            ----------
            email : str, optional
                Email address of your account, by default None
            username : str, optional
                Username of your account, by default None

            Returns
            -------
            dict
                Message from the server
            """
            if not (email or username):
                self.parent.log.error("--> You need to provide username or email")
                return

            data = {}
            if email:
                data["email"] = email
            if username:
                data["username"] = username

            result = self.parent.request(
                "recover/lost",
                method="post",
                json=data,
            )
            msg = result.get("msg")
            self.parent.log.info(f"--> {msg}")
            return result

        def set_my_password(self, token: str, password: str) -> dict:
            """Set a new password using a recovery token

            Token can be obtained through `.reset_password(...)`

            Parameters
            ----------
            token : str
                Token obtained from `reset_password`
            password : str
                New password

            Returns
            -------
            dict
                Message from the server
            """
            result = self.parent.request(
                "recover/reset",
                method="post",
                json={"reset_token": token, "password": password},
            )
            msg = result.get("msg")
            self.parent.log.info(f"--> {msg}")
            return result

        def reset_two_factor_auth(
            self, password: str, email: str = None, username: str = None
        ) -> dict:
            """Start reset procedure for two-factor authentication

            The password and either username of email must be provided.

            Parameters
            ----------
            password: str
                Password of your account
            email : str, optional
                Email address of your account, by default None
            username : str, optional
                Username of your account, by default None

            Returns
            -------
            dict
                Message from the server
            """
            assert email or username, "You need to provide username or email!"
            result = self.parent.request(
                "recover/2fa/lost",
                method="post",
                json={"username": username, "email": email, "password": password},
                retry=False,
            )
            msg = result.get("msg")
            self.parent.log.info(f"--> {msg}")
            return result

        def set_two_factor_auth(self, token: str) -> dict:
            """
            Setup two-factor authentication using a recovery token after you
            have lost access.

            Token can be obtained through `.reset_two_factor_auth(...)`

            Parameters
            ----------
            token : str
                Token obtained from `reset_two_factor_auth`

            Returns
            -------
            dict
                Message from the server
            """
            result = self.parent.request(
                "recover/2fa/reset",
                method="post",
                json={
                    "reset_token": token,
                },
                retry=False,
            )
            if "qr_uri" in result:
                print_qr_code(result)
            else:
                msg = result.get("msg")
                self.parent.log.info(f"--> {msg}")
            return result

        def generate_private_key(self, file_: str = None) -> None:
            """Generate new private key

            Parameters
            ----------
            file_ : str, optional
                Path where to store the private key, by default None
            """
            if not file_:
                self.parent.log.info("--> Using current directory")
                file_ = "private_key.pem"

            if isinstance(file_, str):
                file_ = Path(file_).absolute()

            self.parent.log.info(f"--> Generating private key file: {file_}")
            private_key = RSACryptor.create_new_rsa_key(file_)

            self.parent.log.info("--> Assigning private key to client")
            self.parent.cryptor.private_key = private_key

            self.parent.log.info(
                "--> Encrypting the client and uploading " "the public key"
            )
            self.parent.setup_encryption(file_)

    class Collaboration(ClientBase.SubClient):
        """Collection of collaboration requests"""

        @post_filtering()
        def list(
            self,
            scope: str = "organization",
            name: str = None,
            encrypted: bool = None,
            organization: int = None,
            algorithm_store: int = None,
            page: int = 1,
            per_page: int = 20,
        ) -> List[dict]:
            """View your collaborations

            Parameters
            ----------
            scope : str, optional
                Scope of the list, accepted values are `organization` and
                `global`. In case of `organization` you get the collaborations
                in which your organization participates. If you specify global
                you get the collaborations which you are allowed to see.
            name: str, optional (with LIKE operator)
                Filter collaborations by name
            organization: int, optional
                Filter collaborations by organization id
            algorithm_store: int, optional
                Filter collaborations by algorithm store id that is available for the
                collaboration
            encrypted: bool, optional
                Filter collaborations by whether or not they are encrypted
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the names of the collaborations. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                collaborations. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'collab1')" will only return the collaborations
                with the name 'collab1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'collab1'), ('id', 1)]" will only return the
                collaborations with the name 'collab1' and id 1. Default is None.
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------
            list[dict]
                Containing collabotation information

            Notes
            -----
            - Pagination does not work in combination with scope
              `organization` as pagination is missing at endpoint
              /organization/<id>/collaboration
            """
            params = {
                "page": page,
                "per_page": per_page,
                "name": name,
                "encrypted": encrypted,
                "algorithm_store_id": algorithm_store,
            }
            if scope == "organization":
                params["organization_id"] = self.parent.whoami.organization_id
            elif scope == "global":
                params["organization_id"] = organization
            else:
                self.parent.log.info(
                    "--> Unrecognized `scope`. Needs to be `organization` or `global`"
                )
            return self.parent.request("collaboration", params=params)

        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific collaboration

            Parameters
            ----------
            id_ : int
                Id from the collaboration you want to view
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the collaboration. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                collaboration. Default is None.

            Returns
            -------
            dict
                Containing the collaboration information
            """
            return self.parent.request(f"collaboration/{id_}")

        @post_filtering(iterable=False)
        def create(
            self,
            name: str,
            organizations: list,
            encrypted: bool = False,
            session_restrict_to_same_image: bool = False,
        ) -> dict:
            """Create new collaboration

            Parameters
            ----------
            name : str
                Name of the collaboration
            organizations : list
                List of organization ids which participate in the
                collaboration
            encrypted : bool, optional
                Whenever the collaboration should be encrypted or not,
                by default False
            session_restrict_to_same_image: bool, optional
                Whenever the collaboration should restrict sessions to use the same
                image for data-extraction, pre-processing and compute tasks, by
                default False
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the collaboration. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                collaboration. Default is None.

            Returns
            -------
            dict
                Containing the new collaboration meta-data
            """
            return self.parent.request(
                "collaboration",
                method="post",
                json={
                    "name": name,
                    "organization_ids": organizations,
                    "encrypted": encrypted,
                    "session_restrict_to_same_image": session_restrict_to_same_image,
                },
            )

        def delete(self, id_: int = None, delete_dependents: bool = False) -> None:
            """Deletes a collaboration

            Parameters
            ----------
            id_ : int
                Id of the collaboration you want to delete
            delete_dependents : bool, optional
                Delete the tasks, nodes and studies that are part of the collaboration
                as well. If this is False, and dependents exist, the server will refuse
                to delete the collaboration. Default is False.
            """
            id_ = self.__get_id_or_use_provided_id(id_)
            res = self.parent.request(
                f"collaboration/{id_}",
                method="delete",
                params={"delete_dependents": delete_dependents},
            )
            self.parent.log.info(f"--> {res.get('msg')}")

        @post_filtering(iterable=False)
        def update(
            self,
            id_: int = None,
            name: str = None,
            encrypted: bool = None,
            organizations: List[int] = None,
        ) -> dict:
            """
            Update collaboration information

            Parameters
            ----------
            id_ : int
                Id of the collaboration you want to update. If no id is provided
                the value of setup_collaboration() is used.
            name : str, optional
                New name of the collaboration
            encrypted : bool, optional
                New encryption status of the collaboration
            organizations : list[int], optional
                New list of organization ids which participate in the collaboration
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the collaboration. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                collaboration. Default is None.

            Returns
            -------
            dict
                Containing the updated collaboration information
            """
            id_ = self.__get_id_or_use_provided_id(id_)
            data = {
                "name": name,
                "encrypted": encrypted,
                "organization_ids": organizations,
            }
            data = self._clean_update_data(data)
            return self.parent.request(
                f"collaboration/{id_}",
                method="patch",
                json=data,
            )

        def add_organization(
            self, organization: int, collaboration: int = None
        ) -> List[dict]:
            """
            Add an organization to a collaboration

            Parameters
            ----------
            organization : int
                Id of the organization you want to add to the collaboration
            collaboration : int, optional
                Id of the collaboration you want to add the organization to. If no
                id is provided the value of setup_collaboration() is used.

            Returns
            -------
            list[dict]
                Containing the updated list of organizations in the collaboration
            """
            collaboration = self.__get_id_or_use_provided_id(collaboration)
            return self.parent.request(
                f"collaboration/{collaboration}/organization",
                method="post",
                json={"id": organization},
            )

        def remove_organization(
            self, organization: int, collaboration: int = None
        ) -> List[dict]:
            """
            Remove an organization from a collaboration

            Parameters
            ----------
            organization : int
                Id of the organization you want to remove from the collaboration
            collaboration : int, optional
                Id of the collaboration you want to remove the organization from. If no
                id is provided the value of setup_collaboration() is used.

            Returns
            -------
            list[dict]
                Containing the updated list of organizations in the collaboration
            """
            collaboration = self.__get_id_or_use_provided_id(collaboration)
            return self.parent.request(
                f"collaboration/{collaboration}/organization",
                method="delete",
                json={"id": organization},
            )

        def __get_id_or_use_provided_id(self, id_: int = None) -> int:
            """
            Get the collaboration id from the parent object or use the provided id
            """
            if id_ is None:
                id_ = self.parent.collaboration_id
            self.__validate_id(id_)
            return id_

        def __validate_id(self, id_: int):
            """
            Validate the provided collaboration id
            """
            if id_ is None:
                raise ValueError(
                    "No collaboration id provided. Please provide the id_ argument"
                    "or use `client.setup_collaboration` to set it."
                )

    class Node(ClientBase.SubClient):
        """Collection of node requests"""

        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific node

            Parameters
            ----------
            id_ : int
                Id of the node you want to inspect
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the node. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                node. Default is None.

            Returns
            -------
            dict
                Containing the node meta-data
            """
            return self.parent.request(f"node/{id_}")

        @post_filtering()
        def list(
            self,
            name: str = None,
            organization: int = None,
            collaboration: int = None,
            study: int = None,
            is_online: bool = None,
            ip: str = None,
            last_seen_from: str = None,
            last_seen_till: str = None,
            page: int = 1,
            per_page: int = 20,
        ) -> list[dict]:
            """List nodes

            Parameters
            ----------
            name: str, optional
                Filter by name (with LIKE operator)
            organization: int, optional
                Filter by organization id
            collaboration: int, optional
                Filter by collaboration id. If no id is provided but collaboration was
                defined earlier by user, filtering on that collaboration
            study: int, optional
                Filter by study id
            is_online: bool, optional
                Filter on whether nodes are online or not
            ip: str, optional
                Filter by node VPN IP address
            last_seen_from: str, optional
                Filter if node has been online since date (format: yyyy-mm-dd)
            last_seen_till: str, optional
                Filter if node has been online until date (format: yyyy-mm-dd)
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the node. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                node. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'node1')" will only return the nodes with the name
                'node1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'node1'), ('id', 1)]" will only return the nodes
                with the name 'node1' and id 1. Default is None.
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------

            list of dicts
                Containing meta-data of the nodes
            """
            if collaboration is None:
                collaboration = self.parent.collaboration_id
            params = {
                "page": page,
                "per_page": per_page,
                "name": name,
                "organization_id": organization,
                "collaboration_id": collaboration,
                "study_id": study,
                "ip": ip,
                "last_seen_from": last_seen_from,
                "last_seen_till": last_seen_till,
            }
            if is_online is not None:
                params["status"] = (
                    AuthStatus.ONLINE.value if is_online else AuthStatus.OFFLINE.value
                )
            return self.parent.request("node", params=params)

        @post_filtering(iterable=False)
        def create(
            self,
            collaboration: int | None = None,
            organization: int = None,
            name: str = None,
        ) -> dict:
            """Register new node

            Parameters
            ----------
            collaboration : int
                Collaboration id to which this node belongs. If no ID was provided the,
                collaboration from `client.setup_collaboration()` is used.
            organization : int, optional
                Organization id to which this node belongs. If no id provided
                the users organization is used. Default value is None
            name : str, optional
                Name of the node. If no name is provided the server will
                generate one. Default value is None
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the node. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                node. Default is None.

            Returns
            -------
            dict
                Containing the meta-data of the new node
            """
            if collaboration is None:
                collaboration = self.parent.collaboration_id
                # if still none, raise error
                if collaboration is None:
                    raise ValueError(
                        "No collaboration id provided, please set the "
                        "collaboration id or use `client.setup_collaboration`"
                    )
            if not organization:
                organization = self.parent.whoami.organization_id

            body = {
                "organization_id": organization,
                "collaboration_id": collaboration,
            }
            if name:
                body["name"] = name
            return self.parent.request("node", method="post", json=body)

        @post_filtering(iterable=False)
        def update(self, id_: int, name: str = None, clear_ip: bool = None) -> dict:
            """Update node information

            Parameters
            ----------
            id_ : int
                Id of the node you want to update
            name : str, optional
                New node name, by default None
            clear_ip : bool, optional
                Clear the VPN IP address of the node, by default None
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the node. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                node. Default is None.

            Returns
            -------
            dict
                Containing the meta-data of the updated node
            """
            data = {"name": name, "clear_ip": clear_ip}
            data = self._clean_update_data(data)
            return self.parent.request(
                f"node/{id_}",
                method="patch",
                json=data,
            )

        def delete(self, id_: int) -> None:
            """Deletes a node

            Parameters
            ----------
            id_ : int
                Id of the node you want to delete
            """
            res = self.parent.request(f"node/{id_}", method="delete")
            self.parent.log.info(f"--> {res.get('msg')}")

        def kill_tasks(self, id_: int) -> dict:
            """
            Kill all tasks currently running on a node

            Parameters
            ----------
            id_ : int
                Id of the node of which you want to kill the tasks

            Returns
            -------
            dict
                Message from the server
            """
            return self.parent.request(
                "kill/node/tasks", method="post", json={"id": id_}
            )

    class Organization(ClientBase.SubClient):
        """Collection of organization requests"""

        @post_filtering()
        def list(
            self,
            name: str = None,
            country: int = None,
            collaboration: int = None,
            study: int = None,
            page: int = None,
            per_page: int = None,
        ) -> list[dict]:
            """List organizations

            Parameters
            ----------
            name: str, optional
                Filter by name (with LIKE operator)
            country: str, optional
                Filter by country
            collaboration: int, optional
                Filter by collaboration id. If client.setup_collaboration() was called,
                the previously setup collaboration is used. Default value is None
            study: int, optional
                Filter by study id
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the organization. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                organizations. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'org1')" will only return the organizations with the
                name 'org1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'org1'), ('id', 1)]" will only return the
                organizations with the name 'org1' and id 1. Default is None.
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------
            list[dict]
                Containing meta-data information of the organizations
            """
            if collaboration is None:
                collaboration = self.parent.collaboration_id
            params = {
                "page": page,
                "per_page": per_page,
                "name": name,
                "country": country,
                "collaboration_id": collaboration,
                "study_id": study,
            }
            return self.parent.request("organization", params=params)

        @post_filtering(iterable=False)
        def get(self, id_: int = None) -> dict:
            """View specific organization

            Parameters
            ----------
            id_ : int, optional
                Organization `id` of the organization you want to view.
                In case no `id` is provided it will display your own
                organization, default value is None.
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the organization. Default
                is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                organization. Default is None.


            Returns
            -------
            dict
                Containing the organization meta-data
            """
            if not id_:
                id_ = self.parent.whoami.organization_id

            return self.parent.request(f"organization/{id_}")

        @post_filtering(iterable=False)
        def update(
            self,
            id_: int = None,
            name: str = None,
            address1: str = None,
            address2: str = None,
            zipcode: str = None,
            country: str = None,
            domain: str = None,
            public_key: str = None,
        ) -> dict:
            """Update organization information

            Parameters
            ----------
            id_ : int, optional
                Organization id, by default None
            name : str, optional
                New organization name, by default None
            address1 : str, optional
                Address line 1, by default None
            address2 : str, optional
                Address line 2, by default None
            zipcode : str, optional
                Zipcode, by default None
            country : str, optional
                Country, by default None
            domain : str, optional
                Domain of the organization (e.g. `iknl.nl`), by default None
            public_key : str, optional
                public key, by default None
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the organization. Default
                is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                organization. Default is None.

            Returns
            -------
            dict
                The meta-data of the updated organization
            """
            if not id_:
                id_ = self.parent.whoami.organization_id

            data = {
                "name": name,
                "address1": address1,
                "address2": address2,
                "zipcode": zipcode,
                "country": country,
                "domain": domain,
                "public_key": public_key,
            }
            data = self._clean_update_data(data)

            return self.parent.request(
                f"organization/{id_}",
                method="patch",
                json=data,
            )

        @post_filtering(iterable=False)
        def create(
            self,
            name: str,
            address1: str,
            address2: str,
            zipcode: str,
            country: str,
            domain: str,
            public_key: str = None,
        ) -> dict:
            """Create new organization

            Parameters
            ----------
            name : str
                Name of the organization
            address1 : str
                Street and number
            address2 : str
                City
            zipcode : str
                Zip or postal code
            country : str
                Country
            domain : str
                Domain of the organization (e.g. vantage6.ai)
            public_key : str, optional
                Public key of the organization. This can be set later,
                by default None
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the organization. Default
                is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                organization. Default is None.

            Returns
            -------
            dict
                Containing the information of the new organization
            """
            json_data = {
                "name": name,
                "address1": address1,
                "address2": address2,
                "zipcode": zipcode,
                "country": country,
                "domain": domain,
            }

            if public_key:
                json_data["public_key"] = public_key

            return self.parent.request("organization", method="post", json=json_data)

        def delete(self, id_: int, delete_dependents: bool = False) -> None:
            """Deletes an organization

            Parameters
            ----------
            id_ : int
                Id of the organization you want to delete.
            delete_dependents : bool, optional
                Delete the nodes, users, runs, tasks and roles that are part of
                the organization as well. If this is False, and dependents exist, the
                server will refuse to delete the organization. Default is False.
            """
            res = self.parent.request(
                f"organization/{id_}",
                method="delete",
                params={"delete_dependents": delete_dependents},
            )
            self.parent.log.info(f"--> {res.get('msg')}")

    class User(ClientBase.SubClient):
        @post_filtering()
        def list(
            self,
            username: str = None,
            organization: int = None,
            firstname: str = None,
            lastname: str = None,
            email: str = None,
            role: int = None,
            rule: int = None,
            last_seen_from: str = None,
            last_seen_till: str = None,
            page: int = 1,
            per_page: int = 20,
        ) -> list:
            """List users

            Parameters
            ----------
            username: str, optional
                Filter by username (with LIKE operator)
            organization: int, optional
                Filter by organization id
            firstname: str, optional
                Filter by firstname (with LIKE operator)
            lastname: str, optional
                Filter by lastname (with LIKE operator)
            email: str, optional
                Filter by email (with LIKE operator)
            role: int, optional
                Show only users that have this role id
            rule: int, optional
                Show only users that have this rule id
            last_seen_from: str, optional
                Filter users that have logged on since (format yyyy-mm-dd)
            last_seen_till: str, optional
                Filter users that have logged on until (format yyyy-mm-dd)
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the user. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                users. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'user1')" will only return the users with the name
                'user1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'user1'), ('id', 1)]" will only return the
                users with the name 'user1' and id 1. Default is None.
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------
            list of dicts
                Containing the meta-data of the users
            """
            params = {
                "page": page,
                "per_page": per_page,
                "username": username,
                "organization_id": organization,
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "role_id": role,
                "rule_id": rule,
                "last_seen_from": last_seen_from,
                "last_seen_till": last_seen_till,
            }
            return self.parent.request("user", params=params)

        @post_filtering(iterable=False)
        def get(self, id_: int = None) -> dict:
            """View user information

            Parameters
            ----------
            id_ : int, optional
                User `id`, by default None. When no `id` is provided
                your own user information is displayed
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the user. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                user. Default is None.

            Returns
            -------
            dict
                Containing user information
            """
            if not id_:
                id_ = self.parent.whoami.id_
            return self.parent.request(f"user/{id_}")

        @post_filtering(iterable=False)
        def update(
            self,
            id_: int = None,
            firstname: str = None,
            lastname: str = None,
            organization: int = None,
            rules: list = None,
            roles: list = None,
            email: str = None,
        ) -> dict:
            """Update user details

            In case you do not supply a user_id, your user is being
            updated.

            Parameters
            ----------
            id_ : int
                User `id` from the user you want to update
            firstname : str
                Your first name
            lastname : str
                Your last name
            organization : int
                Organization id of the organization you want to be part
                of. This can only done by super-users.
            rules : list of ints
                USE WITH CAUTION! Rule ids that should be assigned to
                this user. All previous assigned rules will be removed!
            roles : list of ints
                USE WITH CAUTION! Role ids that should be assigned to
                this user. All previous assigned roles will be removed!
            email : str
                New email from the user
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the user. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                user. Default is None.

            Returns
            -------
            dict
                A dict containing the updated user data
            """
            if not id_:
                id_ = self.parent.whoami.id_

            data = {
                "firstname": firstname,
                "lastname": lastname,
                "organization_id": organization,
                "rules": rules,
                "roles": roles,
                "email": email,
            }
            data = self._clean_update_data(data)

            user = self.parent.request(f"user/{id_}", method="patch", json=data)
            return user

        @post_filtering(iterable=False)
        def create(
            self,
            username: str,
            firstname: str,
            lastname: str,
            password: str,
            email: str,
            organization: int = None,
            roles: list = [],
            rules: list = [],
        ) -> dict:
            """Create new user

            Parameters
            ----------
            username : str
                Used to login to the service. This can not be changed
                later.
            firstname : str
                Firstname of the new user
            lastname : str
                Lastname of the new user
            password : str
                Password of the new user
            email : str
                Email address of the new user
            organization : int
                Organization `id` this user should belong to
            roles : list of ints
                Role ids that are assigned to this user. Note that you
                can only assign roles if you own the rules within this
                role.
            rules : list of ints
                Rule ids that are assigned to this user. Note that you
                can only assign rules that you own
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the user. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                user. Default is None.

            Returns
            -------
            dict
                Containing data of the new user
            """
            user_data = {
                "username": username,
                "firstname": firstname,
                "lastname": lastname,
                "password": password,
                "email": email,
                "organization_id": organization,
                "roles": roles,
                "rules": rules,
            }
            return self.parent.request("user", json=user_data, method="post")

        def delete(self, id_: int) -> None:
            """Delete user

            Parameters
            ----------
            id_ : int
                Id of the user you want to delete
            """
            res = self.parent.request(f"user/{id_}", method="delete")
            self.parent.log.info(f'--> {res.get("msg")}')

    class Role(ClientBase.SubClient):
        @post_filtering()
        def list(
            self,
            name: str = None,
            description: str = None,
            organization: int = None,
            rule: int = None,
            user: int = None,
            include_root: bool = None,
            page: int = 1,
            per_page: int = 20,
        ) -> list[dict]:
            """List of roles

            Parameters
            ----------
            name: str, optional
                Filter by name (with LIKE operator)
            description: str, optional
                Filter by description (with LIKE operator)
            organization: int, optional
                Filter by organization id
            rule: int, optional
                Only show roles that contain this rule id
            user: int, optional
                Only show roles that belong to a particular user id
            include_root: bool, optional
                Include roles that are not assigned to any particular
                organization
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the role. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                roles. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'role1')" will only return the roles with the name
                'role1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'role1'), ('id', 1)]" will only return the roles
                with the name 'role1' and id 1. Default is None.
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------
            list[dict]
                Containing roles meta-data
            """
            params = {
                "page": page,
                "per_page": per_page,
                "name": name,
                "description": description,
                "organization_id": organization,
                "rule_id": rule,
                "include_root": include_root,
                "user_id": user,
            }
            return self.parent.request("role", params=params)

        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific role

            Parameters
            ----------
            id_ : int
                Id of the role you want to inspect
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the role. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                role. Default is None.

            Returns
            -------
            dict
                Containing meta-data of the role
            """
            return self.parent.request(f"role/{id_}")

        @post_filtering(iterable=False)
        def create(
            self, name: str, description: str, rules: list, organization: int = None
        ) -> dict:
            """Register new role

            Parameters
            ----------
            name : str
                Role name
            description : str
                Human readable description of the role.
            rules : list
                Rules that this role contains.
            organization : int, optional
                Organization to which this role belongs. In case this is
                not provided the users organization is used. By default
                None.
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the role. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                role. Default is None.

            Returns
            -------
            dict
                Containing meta-data of the new role
            """
            if not organization:
                organization = self.parent.whoami.organization_id
            return self.parent.request(
                "role",
                method="post",
                json={
                    "name": name,
                    "description": description,
                    "rules": rules,
                    "organization_id": organization,
                },
            )

        @post_filtering(iterable=False)
        def update(
            self,
            role: int,
            name: str = None,
            description: str = None,
            rules: list = None,
        ) -> dict:
            """Update role

            Parameters
            ----------
            role : int
                Id of the role that updated
            name : str, optional
                New name of the role, by default None
            description : str, optional
                New description of the role, by default None
            rules : list, optional
                CAUTION! This will not *add* rules but replace them. If
                you remove rules from your own role you lose access. By
                default None
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the role. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                role. Default is None.

            Returns
            -------
            dict
                Containing the updated role data
            """
            data = {
                "name": name,
                "description": description,
                "rules": rules,
            }
            self._clean_update_data(data)
            return self.parent.request(
                f"role/{role}",
                method="patch",
                json=data,
            )

        def delete(self, role: int) -> None:
            """Delete role

            Parameters
            ----------
            role : int
                CAUTION! Id of the role to be deleted. If you remove
                roles that are attached to you, you might lose access!
            """
            res = self.parent.request(f"role/{role}", method="delete")
            self.parent.log.info(f'--> {res.get("msg")}')

    class Task(ClientBase.SubClient):
        @post_filtering(iterable=False)
        def get(self, id_: int, include_results: bool = False) -> dict:
            """View specific task

            Parameters
            ----------
            id_ : int
                Id of the task you want to view
            include_results : bool, optional
                Whenever to include the results or not, by default False
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the task. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                task. Default is None.

            Returns
            -------
            dict
                Containing the task data
            """
            params = {}
            params["include"] = "results" if include_results else None
            return self.parent.request(f"task/{id_}", params=params)

        @post_filtering()
        def list(
            self,
            initiating_org: int = None,
            initiating_user: int = None,
            collaboration: int = None,
            study: int = None,
            store: int = None,
            image: str = None,
            parent: int = None,
            job: int = None,
            name: str = None,
            include_results: bool = False,
            description: str = None,
            database: str = None,
            run: int = None,
            status: str = None,
            user_created: bool = None,
            session: int = None,
            dataframe: int = None,
            page: int = 1,
            per_page: int = 20,
        ) -> dict:
            """List tasks

            Parameters
            ----------
            name: str, optional
                Filter by the name of the task. It will match with a
                Like operator. I.e. E% will search for task names that
                start with an 'E'.
            initiating_org: int, optional
                Filter by initiating organization
            initiating_user: int, optional
                Filter by initiating user
            collaboration: int, optional
                Filter by collaboration. If no id is provided but collaboration was
                defined earlier by setup_collaboration(), filtering on that
                collaboration
            study: int, optional
                Filter by study
            store: int, optional
                Filter by algorithm store from which the algorithm was retrieved
            image: str, optional
                Filter by Docker image name (with LIKE operator)
            parent: int, optional
                Filter by parent task
            job: int, optional
                Filter by job id
            include_results : bool, optional
                Whenever to include the results in the tasks, by default
                False
            description: str, optional
                Filter by description (with LIKE operator)
            database: str, optional
                Filter by database (with LIKE operator)
            run: int, optional
                Only show task that contains this run id
            status: str, optional
                Filter by task status (e.g. 'active', 'pending', 'completed',
                'crashed')
            user_created: bool, optional
                If True, show only top-level tasks created by users. If False,
                show only subtasks created by algorithm containers.
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the tasks. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                tasks. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'task1')" will only return the tasks with the name
                'task1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'task1'), ('id', 1)]" will only return the
                tasks with the name 'task1' and id 1. Default is None.
            session: int, optional
                Filter by session id
            dataframe: int, optional
                Filter by dataframe id
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------
            dict
                dictionary containing the key 'data' which contains the
                tasks and a key 'links' containing the pagination
                metadata
            """
            if collaboration is None:
                collaboration = self.parent.collaboration_id
            # if the param is None, it will not be passed on to the
            # request
            params = {
                "init_org_id": initiating_org,
                "init_user_id": initiating_user,
                "collaboration_id": collaboration,
                "study_id": study,
                "image": image,
                "parent_id": parent,
                "job_id": job,
                "name": name,
                "page": page,
                "per_page": per_page,
                "description": description,
                "database": database,
                "run_id": run,
                "status": status,
                "store_id": store,
                "session_id": session,
                "dataframe_id": dataframe,
            }
            includes = []
            if include_results:
                includes.append("results")
            params["include"] = includes
            if user_created is not None:
                params["is_user_created"] = 1 if user_created else 0

            return self.parent.request("task", params=params)

        @post_filtering(iterable=False)
        def create(
            self,
            organizations: list | None,
            name: str,
            image: str,
            description: str,
            input_: dict,
            session: int | None = None,
            collaboration: int | None = None,
            study: int | None = None,
            store: int | None = None,
            server_url: str | None = None,
            databases: list[dict] | None = None,
        ) -> dict:
            """Create a new task

            Parameters
            ----------
            organizations : list
                Organization ids (within the collaboration) which need
                to execute this task
            name : str
                Human readable name
            image : str
                Docker image name which contains the algorithm
            description : str
                Human readable description
            input_ : dict
                Algorithm input
            session : int, optional
                ID of the session to which this task belongs. If not set, the
                session id of the client needs to be set. Default is None.
            collaboration : int, optional
                ID of the collaboration to which this task belongs. Should be set if
                the study is not set
            study : int, optional
                ID of the study to which this task belongs. Should be set if the
                collaboration is not set
            store : int, optional
                ID of the algorithm store to retrieve the algorithm from
            server_url: str, optional
                URL of the server on which the task is created. This should be given if
                the algorithm is retrieved from an algorithm store, and the server does
                not contain its own URL in the configuration (you will be alerted of
                this in an error message).
            databases: list[dict], optional
                Databases to be used at the node. Each dict should contain
                at least a 'label' key. Additional keys are 'query' (if using
                SQL/SPARQL databases), 'sheet_name' (if using Excel databases),
                and 'preprocessing' information.
            field: str, optional
                Which data field to keep in the returned dict. For instance,
                "field='name'" will only return the name of the task. Default is None.
            fields: list[str], optional
                Which data fields to keep in the returned dict. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                task. Default is None

            Returns
            -------
            dict
                A dictionairy containing data on the created task, or a message
                from the server if the task could not be created
            """
            assert self.parent.cryptor, "Encryption has not yet been setup!"

            if session is None and self.parent.session_id is None:
                raise ValueError(
                    "No session specified! Cannot create task without a session."
                )

            if collaboration is None:
                collaboration = self.parent.collaboration_id
            if not collaboration and not study:
                raise ValueError(
                    "Either a collaboration or a study should be specified"
                )

            if organizations is None:
                raise ValueError(
                    "No organizations specified! Cannot create task without "
                    "assigning it to at least one organization."
                )

            if store is None:
                store = self.parent.store.store_id
                if store is not None:
                    self.parent.log.info(
                        "Using algorithm store with id='%s' to retrieve the algorithm.",
                        self.parent.store.store_id,
                    )

            if databases is None:
                databases = []
            databases = self._parse_arg_databases(databases)

            # Data will be serialized in JSON.
            serialized_input = serialize(input_)

            # Encrypt the input per organization using that organization's
            # public key.
            organization_json_list = []
            for org_id in organizations:
                pub_key = self.parent.request(f"organization/{org_id}").get(
                    "public_key"
                )
                organization_json_list.append(
                    {
                        "id": org_id,
                        "input": self.parent.cryptor.encrypt_bytes_to_str(
                            serialized_input, pub_key
                        ),
                    }
                )

            params = {
                "name": name,
                "image": image,
                "description": description,
                "organizations": organization_json_list,
                "databases": databases,
                "session_id": session,
            }

            if collaboration:
                params["collaboration_id"] = collaboration
            if study:
                params["study_id"] = study
            if store:
                params["store_id"] = store
            if server_url:
                params["server_url"] = server_url

            return self.parent.request(
                "task",
                method="post",
                json=params,
            )

        @staticmethod
        def _parse_arg_databases(databases: list[dict] | str) -> list[dict]:
            """Parse the databases argument

            Parameters
            ----------
            databases: list[dict] | str
                Each dict should contain at least a 'label' key. A single str
                can be passed and will be interpreted as a single database with
                that label.

            Returns
            -------
            list[dict]
                The parsed databases argument

            Raises
            ------
            ValueError: if 'label' is missing from the database dict or an
                        invalid label is provided.

            Note
            ----
            We are looking before we leap (LBYL) rather than attempting to
            catch an exception later on (EAFP) because the task will be created
            on the server before nodes might even get a chance to complain.
            """
            if isinstance(databases, str):
                # it is not unlikely that users specify a single database as a
                # str, in that case we convert it to a list
                databases = [{"label": databases}]

            for db in databases:
                try:
                    label_input = db.get("label")
                except AttributeError:
                    raise ValueError(
                        "Databases specified should be a list of dicts with"
                        "label keys or a single str"
                    )
                if not label_input or not isinstance(label_input, str):
                    raise ValueError(
                        "Each database should have a 'label' key with a string" "value."
                    )
                # Labels will become part of env var names in algo container,
                # some chars are not allowed in some shells.
                if not label_input.isidentifier():
                    raise ValueError(
                        "Database labels should be made up of letters, digits"
                        " (except first character) and underscores only. "
                        f"Invalid label: {db.get('label')}"
                    )
            return databases

        def delete(self, id_: int) -> None:
            """Delete a task

            Also removes the related runs.

            Parameters
            ----------
            id_ : int
                Id of the task to be removed
            """
            msg = self.parent.request(f"task/{id_}", method="delete")
            self.parent.log.info(f"--> {msg}")

        def kill(self, id_: int) -> dict:
            """Kill a task running on one or more nodes

            Note that this does not remove the task from the database, but
            merely halts its execution (and prevents it from being restarted).

            Parameters
            ----------
            id_ : int
                Id of the task to be killed

            Returns
            -------
            dict
                Message from the server
            """
            msg = self.parent.request("/kill/task", method="post", json={"id": id_})
            self.parent.log.info(f"--> {msg}")

    class Run(ClientBase.SubClient):
        @post_filtering(iterable=False)
        def get(self, id_: int, include_task: bool = False) -> dict:
            """View a specific run

            Parameters
            ----------
            id_ : int
                id of the run you want to inspect
            include_task : bool, optional
                Whenever to include the task or not, by default False
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the run. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the name and id of the
                run. Default is None.

            Returns
            -------
            dict
                Containing the run data
            """
            self.parent.log.info("--> Attempting to decrypt results!")

            # get run from the API
            params = {"include": "task"} if include_task else {}
            run = self.parent.request(endpoint=f"run/{id_}", params=params)

            # decrypt input
            run = self._decrypt_input(run_data=run, is_single_run=True)

            return run

        @post_filtering()
        def list(
            self,
            task: int = None,
            organization: int = None,
            state: str = None,
            node: int = None,
            include_task: bool = False,
            started: tuple[str, str] = None,
            assigned: tuple[str, str] = None,
            finished: tuple[str, str] = None,
            port: int = None,
            page: int = None,
            per_page: int = None,
        ) -> dict | list[dict]:
            """List runs

            Parameters
            ----------
            task: int, optional
                Filter by task id
            organization: int, optional
                Filter by organization id
            state: int, optional
                Filter by state: ('open',)
            node: int, optional
                Filter by node id
            include_task : bool, optional
                Whenever to include the task or not, by default False
            started: tuple[str, str], optional
                Filter on a range of start times (format: yyyy-mm-dd)
            assigned: tuple[str, str], optional
                Filter on a range of assign times (format: yyyy-mm-dd)
            finished: tuple[str, str], optional
                Filter on a range of finished times (format: yyyy-mm-dd)
            port: int, optional
                Port on which run was computed
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the runs. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                runs. Default is None.
            page: int, optional
                Pagination page number, defaults to 1
            per_page: int, optional
                Number of items per page, defaults to 20

            Returns
            -------
            dict | list[dict]
                A dictionary containing the key 'data' which contains a list of
                runs, and a key 'links' which contains the pagination metadata.
            """
            includes = []
            if include_task:
                includes.append("task")

            s_from, s_till = started if started else (None, None)
            a_from, a_till = assigned if assigned else (None, None)
            f_from, f_till = finished if finished else (None, None)

            params = {
                "task_id": task,
                "organization_id": organization,
                "state": state,
                "node_id": node,
                "page": page,
                "per_page": per_page,
                "include": includes,
                "started_from": s_from,
                "started_till": s_till,
                "assigned_from": a_from,
                "assigned_till": a_till,
                "finished_from": f_from,
                "finished_till": f_till,
                "port": port,
            }

            # get runs from the API
            runs = self.parent.request(endpoint="run", params=params)

            # decrypt input data
            runs = self._decrypt_input(run_data=runs, is_single_run=False)

            return runs

        @post_filtering(iterable=True)
        def from_task(self, task_id: int, include_task: bool = False) -> list[dict]:
            """
            Get all algorithm runs from a specific task

            Parameters
            ----------
            task_id : int
                Id of the task to get results from
            include_task : bool, optional
                Whenever to include the task or not, by default False
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the runs. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                runs. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('name', 'run1')" will only return the runs with the name
                'run1'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('name', 'run1'), ('id', 1)]" will only return the runs
                with the name 'run1' and id 1. Default is None.

            Returns
            -------
            list[dict]
                Containing the results
            """
            self.parent.log.info("--> Attempting to decrypt results!")

            # get all algorithm runs from a specific task
            params = {}
            if include_task:
                params["include"] = "task"
            if task_id:
                params["task_id"] = task_id
            runs = self.parent.request(endpoint="run", params=params)

            # decrypt input data
            runs = self._decrypt_input(run_data=runs, is_single_run=False)

            return runs

        def _decrypt_input(self, run_data: dict, is_single_run: bool) -> dict:
            """
            Wrapper function to decrypt and deserialize the input of one or
            more runs

            Parameters
            ----------
            run_data : dict
                The data of the run(s) to decrypt
            is_single_run : bool
                Whether the run_data is a single run or a list of runs

            Returns
            -------
            dict
                Data on the algorithm run(s) with decrypted input
            """
            return self.parent._decrypt_field(
                data=run_data, field="input", is_single_resource=is_single_run
            )

    class Result(ClientBase.SubClient):
        """
        Client to get the results of one or multiple algorithm runs
        """

        def get(self, id_: int) -> dict:
            """View a specific result

            Parameters
            ----------
            id_ : int
                id of the run you want to inspect

            Returns
            -------
            dict
                Containing the run data
            """
            self.parent.log.info("--> Attempting to decrypt results!")

            result = self.parent.request(endpoint=f"result/{id_}")
            result = self._decrypt_result(result_data=result, is_single_result=True)

            return result["result"]

        def from_task(self, task_id: int):
            """
            Get all results from a specific task

            Parameters
            ----------
            task_id : int
                Id of the task to get results from

            Returns
            -------
            list[dict]
                Containing the results
            """
            self.parent.log.info("--> Attempting to decrypt results!")

            results = self.parent.request("result", params={"task_id": task_id})
            results = self._decrypt_result(results, False)
            return results

        def _decrypt_result(self, result_data: dict, is_single_result: bool) -> dict:
            """
            Wrapper function to decrypt and deserialize the input of one or
            more runs

            Parameters
            ----------
            result_data : dict
                The data of the run(s) to decrypt
            is_single_result : bool
                Whether the result_data is a single result or a list of results

            Returns
            -------
            dict
                Data on the algorithm run(s) with decrypted input
            """
            return self.parent._decrypt_field(
                data=result_data, field="result", is_single_resource=is_single_result
            )

    class Rule(ClientBase.SubClient):
        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific rule

            Parameters
            ----------
            id_ : int
                Id of the rule you want to view
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the rule. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                rule. Default is None.

            Returns
            -------
            dict
                Containing the information about this rule
            """
            return self.parent.request(f"rule/{id_}")

        @post_filtering()
        def list(
            self,
            name: str = None,
            operation: str = None,
            scope: str = None,
            role: int = None,
            page: int = 1,
            per_page: int = 20,
        ) -> list:
            """List of all available rules

            Parameters
            ----------
            name: str, optional
                Filter by rule name
            operation: str, optional
                Filter by operation
            scope: str, optional
                Filter by scope
            role: int, optional
                Only show rules that belong to this role id
            field: str, optional
                Which data field to keep in the result. For instance, "field='name'"
                will only return the name of the rule. Default is None.
            fields: list[str], optional
                Which data fields to keep in the result. For instance,
                "fields=['name', 'id']" will only return the names and ids of the
                rule. Default is None.
            filter_: tuple, optional
                Filter the result on key-value pairs. For instance,
                "filter_=('scope', 'own')" will only return the rules with the scope
                'own'. Default is None.
            filters: list[tuple], optional
                Filter the result on multiple key-value pairs. For instance,
                "filters=[('scope', 'own'), ('name', 'node')]" will only return the
                rules with the scope 'own' and name 'node'. Default is None.
            page: int, optional
                Pagination page, by default 1
            per_page: int, optional
                Number of items on a single page, by default 20

            Returns
            -------
            list of dicts
                Containing all the rules from the vantage6 server
            """
            params = {
                "page": page,
                "per_page": per_page,
                "name": name,
                "operation": operation,
                "scope": scope,
                "role_id": role,
            }
            return self.parent.request("rule", params=params)


# Alias the UserClient to Client for easy usage for Python users
Client = UserClient
