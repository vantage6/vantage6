import abc
import itertools
import logging
import time
import json as json_lib
from pathlib import Path

import requests

from vantage6.common.encryption import RSACryptor, DummyCryptor
from vantage6.common.enum import TaskStatus
from vantage6.common.globals import (
    STRING_ENCODING,
    INTERVAL_MULTIPLIER,
    MAX_INTERVAL,
)

module_name = __name__.split(".")[1]


@staticmethod
def _log_completion(task_id: int, start_time: float, log_animation: bool) -> None:
    """
    Log the completion message for a task.

    Parameters
    ----------
    task_id : int
        ID of the completed task.
    start_time : float
        The time when the task started.
    log_animation : bool
        Whether to log the message as an animation or a regular log.
    """
    elapsed_time = int(time.time() - start_time)
    message = f"Task {task_id} completed in {elapsed_time} seconds."

    if log_animation:
        print(f"\r{message}                     ")
    else:
        logging.info(message)


@staticmethod
def _log_progress(
    task_id: int, start_time: float, log_animation: bool, animation_frame: str
) -> None:
    """
    Log the progress message for a task.

    Parameters
    ----------
    task_id : int
        ID of the task in progress.
    start_time : float
        The time when the task started.
    log_animation : bool
        Whether to log the message as an animation or a regular log.
    animation_frame : str
        The current frame of the animation.
    """
    elapsed_time = int(time.time() - start_time)
    message = f"{animation_frame} Waiting for task {task_id}... ({elapsed_time}s)"

    if log_animation:
        print(f"\r{message}", end="")
    else:
        logging.info(message)


class ClientBase(object):
    """Common interface to the central server.

    Contains the basis for all other clients, e.g. UserClient, NodeClient and
    AlgorithmClient. This includes a basic interface to authenticate, send
    generic requests, create tasks and retrieve results.
    """

    def __init__(self, server_url: str, auth_url: str | None = None) -> None:
        """Basic setup for the client

        Parameters
        ----------
        server_url : str
            URL of the vantage6 server you want to connect to
        auth_url : str
            URL of the vantage6 auth server (keycloak) you want to authenticate with
        """

        self.log = logging.getLogger(module_name)

        # server settings
        self.__server_url = server_url
        self.__auth_url = auth_url

        # tokens
        self._access_token = None
        self._refresh_token = None
        self._refresh_url = None

        self.cryptor = None
        self.whoami = None

    @property
    def name(self) -> str:
        """
        Return the node's/client's name

        Returns
        -------
        str
            Name of the user or node
        """
        return self.whoami.name

    @property
    def headers(self) -> dict:
        """
        Defines headers that are sent with each request. This includes the
        authorization token.

        Returns
        -------
        dict
            Headers
        """
        if self._access_token:
            return {"Authorization": "Bearer " + self._access_token}
        else:
            return {}

    @property
    def token(self) -> str:
        """
        JWT Authorization token

        Returns
        -------
        str
            JWT token
        """
        return self._access_token

    @property
    def server_url(self) -> str:
        """
        URL of the vantage6 server

        Returns
        -------
        str
            Host address of the vantage6 server
        """
        return self.__server_url

    @property
    def auth_url(self) -> str:
        """
        URL of the vantage6 auth server (keycloak)
        """
        return self.__auth_url

    def generate_path_to(self, endpoint: str, is_for_algorithm_store: bool) -> str:
        """Generate URL to endpoint using host, port and endpoint

        Parameters
        ----------
        endpoint : str
            endpoint to which a fullpath needs to be generated
        is_for_algorithm_store : bool
            Whether the request is for the algorithm store or not

        Returns
        -------
        str
            URL to the endpoint
        """
        if not is_for_algorithm_store:
            base_path = self.server_url
        else:
            try:
                base_path = self.store.url
            except AttributeError as exc:
                raise AttributeError(
                    "Algorithm store not set. Please set the algorithm store first with"
                    " `client.algorithm_store.set()`."
                ) from exc
        if endpoint.startswith("/"):
            path = base_path + endpoint
        else:
            path = base_path + "/" + endpoint

        return path

    def request(
        self,
        endpoint: str,
        json: dict = None,
        method: str = "get",
        params: dict = None,
        headers: dict = None,
        first_try: bool = True,
        retry: bool = True,
        attempts_on_timeout: int = None,
        is_for_algorithm_store: bool = False,
    ) -> dict:
        """Create http(s) request to the vantage6 server

        Parameters
        ----------
        endpoint : str
            Endpoint of the server
        json : dict, optional
            payload, by default None
        method : str, optional
            Http verb, by default 'get'
        params : dict, optional
            URL parameters, by default None
        headers : dict, optional
            Additional headers to be sent with the request, by default None
        first_try : bool, optional
            Whether this is the first attempt of this request. Default True.
        retry: bool, optional
            Try request again after refreshing the token. Default True.
        attempts_on_timeout: int, optional
            Number of attempts to make when a timeout occurs. Default None
            which leads to unlimited amount of attempts.
        is_for_algorithm_store: bool, optional
            Whether the request is for the algorithm store. Default False.

        Returns
        -------
        dict
            Response of the server
        """
        store_valid = self.__check_algorithm_store_valid(is_for_algorithm_store)
        if not store_valid:
            return

        # get appropiate method
        rest_method = {
            "get": requests.get,
            "post": requests.post,
            "put": requests.put,
            "patch": requests.patch,
            "delete": requests.delete,
        }.get(method.lower(), requests.get)

        # send request to server
        url = self.generate_path_to(endpoint, is_for_algorithm_store)
        self.log.debug(f"Making request: {method.upper()} | {url} | {params}")

        # add additional headers if any are given
        headers = self.headers if headers is None else headers | self.headers

        timeout_attempts = 0
        while True:
            try:
                response = rest_method(url, json=json, headers=headers, params=params)
                break
            except requests.exceptions.ConnectionError as exc:
                # we can safely retry as this is a connection error. And we
                # keep trying (unless a max number of attempts is given)!
                timeout_attempts += 1
                if (
                    attempts_on_timeout is not None
                    and timeout_attempts > attempts_on_timeout
                ):
                    return {"msg": "Connection error"}
                self.log.error("Connection error... Retrying")
                self.log.info(exc)
                time.sleep(1)

        # TODO: should check for a non 2xx response
        if response.status_code > 210:
            self.log.error(f"Server responded with error code: {response.status_code}")
            try:
                msg = response.json().get("msg", "")
                # remove dot at the end of the message if it is there to prevent double
                # dots in the log message
                if msg.endswith("."):
                    msg = msg[:-1]
                self.log.error("msg: %s. Endpoint: %s", msg, endpoint)
                if response.json().get("errors"):
                    self.log.error("errors:" + str(response.json().get("errors")))
            except json_lib.JSONDecodeError:
                self.log.error("Did not find a message from the server")
                self.log.error(response.content)

            if retry:
                if first_try:
                    self.obtain_new_token()
                    return self.request(
                        endpoint,
                        json,
                        method,
                        params,
                        headers,
                        first_try=False,
                        attempts_on_timeout=attempts_on_timeout,
                        is_for_algorithm_store=is_for_algorithm_store,
                    )
                else:
                    self.log.error("Nope, refreshing the token didn't fix it.")

        return response.json()

    def setup_encryption(self, private_key_file: str | None) -> None:
        """Use private key file to setup encryption of sensitive data.

        This function will use the private key file to setup encryption and decryption
        of task input and results. It needs to be called once per client in encrypted
        collaborations to ensure that the client can read and write encrypted data.

        A Cryptor object that handles encryption and decryption will be attached to the
        client, after verifying that the public key at the server matches the provided
        private key. In case the server's public key does not match with the local
        public key, the local one is uploaded to the server.

        Parameters
        ----------
        private_key_file : str | None
            File path of the private key file, or None if encryption is not enabled

        Raises
        ------
        AssertionError
            If the client is not authenticated
        """
        assert self._access_token, "Encryption can only be setup after authentication"
        assert (
            self.whoami.organization_id
        ), "Organization unknown... Did you authenticate?"

        if private_key_file is None:
            self.cryptor = DummyCryptor()
            return

        if isinstance(private_key_file, str):
            private_key_file = Path(private_key_file)

        cryptor = RSACryptor(private_key_file)

        # check if the public-key is the same on the server. If this is
        # not the case, this node will not be able to read any messages
        # that are send to him! If this is the case, the new public_key
        # will be uploaded to the central server
        organization = self.request(f"organization/{self.whoami.organization_id}")
        pub_key = organization.get("public_key")
        upload_pub_key = False

        if pub_key:
            if cryptor.verify_public_key(pub_key):
                self.log.info("Public key matches the server key! Good to go!")

            else:
                self.log.critical(
                    "Local public key does not match server public key. "
                    "You will not able to read any messages that are intended "
                    "for you!"
                )
                upload_pub_key = True
        else:
            upload_pub_key = True

        # upload public key if required
        if upload_pub_key:
            self.request(
                f"organization/{self.whoami.organization_id}",
                method="patch",
                json={"public_key": cryptor.public_key_str},
            )
            self.log.info("The public key on the server is updated!")

        self.cryptor = cryptor

    @abc.abstractmethod
    def authenticate(self) -> None:
        """Authenticate to vantage6 via keycloak."""
        return

    @abc.abstractmethod
    def obtain_new_token(self) -> None:
        """Obtain a new token.

        Depending on the type of entity authenticating, this may use a refresh token
        """
        return

    def _decrypt_data(self, encrypted_data: str) -> bytes:
        """Helper to decrypt the input of an algorithm run

        Keys are replaced, but object reference remains intact: changes are
        made *in-place*.

        Parameters
        ----------
        encrypted_data: str
            The encrypted algorithm data

        Returns
        -------
        bytes
            The decrypted algorithm run data

        Raises
        ------
        AssertionError
            Encryption has not been initialized
        """
        assert self.cryptor, "Encryption has not been initialized"
        cryptor = self.cryptor
        try:
            # TODO this only works when the runs belong to the
            # same organization... We should make different implementation
            # of get_results
            data = cryptor.decrypt_str_to_bytes(encrypted_data)

        except Exception as e:
            self.log.exception(e)

        return data

    def _decrypt_field(self, data: dict, field: str, is_single_resource: bool) -> dict:
        """
        Wrapper function to decrypt and deserialize the a field of one or more
        resources

        This can be used to decrypt and deserialize data of algorithm runs.
        algorithm runs.

        Parameters
        ----------
        run_data : dict
            The data of which to decrypt a field
        field : str
            The field to decrypt and deserialize
        is_single_resource : bool
            Whether the data is of a single resource or a list of resources

        Returns
        -------
        dict
            Decrypted data on the algorithm run(s)
        """

        def _decrypt_and_decode(value: str, field: str):
            decrypted = self._decrypt_data(value)
            if not isinstance(decrypted, bytes):
                self.log.error(
                    "The field %s is not properly encoded. Expected bytes, got" " %s.",
                    field,
                    type(decrypted),
                )
                if isinstance(decrypted, str):
                    self.log.error(
                        "Skipping decoding as string is detected for %s", field
                    )
                    return decrypted
            try:
                return decrypted.decode(STRING_ENCODING)
            except Exception:
                self.log.error(
                    "Failed to decode the field %s. Skipping decoding, "
                    "returning bytes object.",
                    field,
                )
                return decrypted

        if is_single_resource:
            if data.get(field):
                data[field] = _decrypt_and_decode(data[field], field)
        else:
            # for multiple resources, data is in a 'data' field of a dict
            for resource in data["data"]:
                if resource.get(field):
                    resource[field] = _decrypt_and_decode(resource[field], field)

        return data

    def __check_algorithm_store_valid(self, is_for_algorithm_store: bool) -> bool:
        """
        Check if the algorithm store is properly setup before handling algorithm store
        request

        Parameters
        ----------
        is_for_algorithm_store : bool
            Whether the request is for the algorithm store or not

        Returns
        -------
        bool
            Whether the algorithm store is properly setup
        """
        if is_for_algorithm_store:
            try:
                int(self.store.store_id)
                return True
            except AttributeError:
                self.log.error(
                    "Algorithm store not set. Please set the algorithm store first with"
                    " `client.store.set()`."
                )
                return False
        return True

    def wait_for_task_completion(
        self,
        request_func,
        task_id: int,
        interval: float = 1,
        log_animation: bool = True,
    ) -> None:
        """
        Utility function to wait for a task to complete.

        Parameters
        ----------
        request_func : Callable
            Function to make requests to the server.
        task_id : int
            ID of the task to wait for.
        interval : float
            Initial interval in seconds between status checks.
        log_animation : bool
            Whether to log an animation (default: True). If False, logs will be
            written as separate lines.
        """
        start_time = time.time()
        animation = itertools.cycle(["|", "/", "-", "\\"])

        while True:
            response = request_func(f"task/{task_id}/status")
            status = response.get("status")

            if TaskStatus.has_finished(status):
                _log_completion(task_id, start_time, log_animation)
                break

            _log_progress(task_id, start_time, log_animation, next(animation))
            time.sleep(interval)
            interval = min(interval * INTERVAL_MULTIPLIER, MAX_INTERVAL)

    class SubClient:
        """
        Create sub groups of commands using this SubClient

        For example, the class `vantage6.client.subclients.study.Study` defines the
        commands that can be run on studies. These are accessible for the user as
        subclient: `client.study`.

        Parameters
        ----------
        parent : UserClient | AlgorithmClient
            The parent client
        """

        def __init__(self, parent) -> None:
            # If the parent has a parent, use that as the parent - we don't want
            # grandparents and so on.
            # TODO maybe this should ideally get a name of 'main_client' or something
            if hasattr(parent, "parent"):
                self.parent: ClientBase = parent.parent
            else:
                self.parent: ClientBase = parent

        @staticmethod
        def _clean_update_data(data: dict) -> dict:
            """
            Remove key-value pair where the value is equal to `None`

            Parameters
            ----------
            data: dict
                Items to filter

            Returns
            -------
            dict
                Input `data` but with the key-value pair where value is `None` removed
            """
            return {k: v for k, v in data.items() if v is not None}
