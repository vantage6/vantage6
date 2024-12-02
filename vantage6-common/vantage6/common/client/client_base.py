import logging
import time
import requests
import json as json_lib

from pathlib import Path

from vantage6.common.exceptions import AuthenticationException
from vantage6.common.encryption import RSACryptor, DummyCryptor
from vantage6.common.globals import STRING_ENCODING
from vantage6.common.client.utils import print_qr_code

module_name = __name__.split(".")[1]


class ClientBase(object):
    """Common interface to the central server.

    Contains the basis for all other clients, e.g. UserClient, NodeClient and
    AlgorithmClient. This includes a basic interface to authenticate, send
    generic requests, create tasks and retrieve results.
    """

    def __init__(self, host: str, port: int, path: str = "/api") -> None:
        """Basic setup for the client

        Parameters
        ----------
        host : str
            Address (including protocol, e.g. `https://`) of the vantage6 server
        port : int
            port number to which the server listens
        path : str, optional
            path of the api, by default '/api'
        """

        self.log = logging.getLogger(module_name)

        # server settings
        self.__host = host
        self.__port = port
        self.__api_path = path

        # tokens
        self._access_token = None
        self.__refresh_token = None
        self.__refresh_url = None

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
    def host(self) -> str:
        """
        Host including protocol (HTTP/HTTPS)

        Returns
        -------
        str
            Host address of the vantage6 server
        """
        return self.__host

    @property
    def port(self) -> int:
        """
        Port on which vantage6 server listens

        Returns
        -------
        int
            Port number
        """
        return self.__port

    @property
    def path(self) -> str:
        """
        Path/endpoint at the server where the api resides

        Returns
        -------
        str
            Path to the api
        """
        return self.__api_path

    @property
    def base_path(self) -> str:
        """
        Full path to the server URL. Combination of host, port and api-path

        Returns
        -------
        str
            Server URL
        """
        if self.__port:
            return f"{self.host}:{self.port}{self.__api_path}"

        return f"{self.host}{self.__api_path}"

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
            base_path = self.base_path
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
                    self.refresh_token()
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

    def authenticate(self, credentials: dict, path: str = "token/user") -> bool:
        """Authenticate to the vantage6-server

        It allows users, nodes and containers to sign in. Credentials can
        either be a username/password combination or a JWT authorization
        token.

        Parameters
        ----------
        credentials : dict
            Credentials used to authenticate
        path : str, optional
            Endpoint used for authentication. This differs for users, nodes and
            containers, by default "token/user"

        Raises
        ------
        Exception
            Failed to authenticate

        Returns
        -------
        Bool
            Whether or not user is authenticated. Alternative is that user is
            redirected to set up two-factor authentication
        """
        if "username" in credentials:
            self.log.debug(f"Authenticating user {credentials['username']}...")
        elif "api_key" in credentials:
            self.log.debug("Authenticating node...")

        # authenticate to the central server
        url = self.generate_path_to(path, is_for_algorithm_store=False)
        response = requests.post(url, json=credentials)
        if response.status_code == 404:
            self.log.error(
                "Server not found at %s. Please check the address and whether the "
                "server is running!",
                url,
            )
            self.log.info(
                "If the server is running and reachable, %s/health should give a "
                "response.",
                self.base_path,
            )
            return False

        # handle negative responses
        data = response.json()
        if response.status_code > 200:
            self.log.critical(f"Failed to authenticate: {data.get('msg')}")
            if response.status_code == 401:
                raise AuthenticationException("Failed to authenticate")
            else:
                raise Exception("Failed to authenticate")

        if "qr_uri" in data:
            print_qr_code(data)
            return False
        else:
            # Check if there is an access token. If not, there is a problem
            # with authenticating
            if "access_token" not in data:
                if "msg" in data:
                    raise Exception(data["msg"])
                else:
                    raise Exception("No access token in authentication response!")

            # store tokens in object
            self.log.info("Successfully authenticated")
            self._access_token = data.get("access_token")
            self.__refresh_token = data.get("refresh_token")
            self.__refresh_url = data.get("refresh_url")
            return True

    def refresh_token(self) -> None:
        """Refresh an expired token using the refresh token

        Raises
        ------
        Exception
            Authentication Error!
        AssertionError
            Refresh URL not found
        """
        self.log.info("Refreshing token")
        assert self.__refresh_url, "Refresh URL not found, did you authenticate?"

        # if no port is specified explicit, then it should be omit the
        # colon : in the path. Similar (but different) to the property
        # base_path
        if self.__port:
            url = f"{self.__host}:{self.__port}{self.__refresh_url}"
        else:
            url = f"{self.__host}{self.__refresh_url}"

        # send request to server
        response = requests.post(
            url, headers={"Authorization": "Bearer " + self.__refresh_token}
        )

        # server says no!
        if response.status_code != 200:
            self.log.critical("Could not refresh token")
            raise Exception("Authentication Error!")

        self._access_token = response.json()["access_token"]
        self.__refresh_token = response.json()["refresh_token"]

    def _decrypt_input(self, input_: str) -> bytes:
        """Helper to decrypt the input of an algorithm run

        Keys are replaced, but object reference remains intact: changes are
        made *in-place*.

        Parameters
        ----------
        input_: str
            The encrypted algorithm input

        Returns
        -------
        bytes
            The decrypted algorithm run input

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
            input_ = cryptor.decrypt_str_to_bytes(input_)

        except Exception as e:
            self.log.exception(e)

        return input_

    def _decrypt_field(self, data: dict, field: str, is_single_resource: bool) -> dict:
        """
        Wrapper function to decrypt and deserialize the a field of one or more
        resources

        This can be used to decrypt and deserialize input and results of
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
            Data on the algorithm run(s) with decrypted input
        """

        def _decrypt_and_decode(value: str, field: str):
            decrypted = self._decrypt_input(value)
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
