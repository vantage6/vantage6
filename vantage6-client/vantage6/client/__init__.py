"""
Server IO

This module is an interface to the central server.
"""
import logging
import requests
import jwt
import typing
import jwt
import requests

from vantage6.common import bytes_to_base64s, base64s_to_bytes
from vantage6.client import serialization, deserialization
from vantage6.client.encryption import CryptorBase, RSACryptor, DummyCryptor


module_name = __name__.split('.')[1]


class ServerInfo(typing.NamedTuple):
    """ Data-class to store the server info
    """
    host: str
    port: int
    path: str


class WhoAmI(typing.NamedTuple):
    """ Data-class to store Authenticable information in.
    """
    type_: str
    id_: int
    name: str
    organization_name: str
    organization_id: int

    def __repr__(self) -> str:
        return (f"<WhoAmI "
                f"name={self.name}, "
                f"type={self.type_}, "
                f"organization={self.organization_name}"
                ">")


class ClientBase(object):
    """Common interface to the central server.

    It manages the connection settings and constructs request paths,
    allows for authentication task creation and result retrieval.
    """

    def __init__(self, host: str, port: int, path: str = '/api',
                 private_key_file: str = None):
        """ Initialization of the communcation protocol class.

            :param host: hostname/ip including protocol (http/https)
            :param port: port to which the central server listens
            :param path: endpoint at the server to where the server
                side application runs
            :param private_key_file: local path to the private key file
                of the organization.

            TODO private_key_file is not used here
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
    def name(self):
        """Return the node's/client's name."""
        return self.whoami.name

    @property
    def headers(self):
        """Headers that are send with each request."""
        if self._access_token:
            return {'Authorization': 'Bearer ' + self._access_token}
        else:
            return {}

    @property
    def token(self):
        """Authorization token."""
        return self._access_token

    @property
    def host(self):
        """Host including protocol (HTTP/HTTPS)."""
        return self.__host

    @property
    def port(self):
        """Port from the central server."""
        return self.__port

    @property
    def path(self):
        """Path/endpoint from the server where the api resides."""
        return self.__api_path

    @property
    def base_path(self):
        """Combination of host, port and api-path."""
        if self.__port:
            return f"{self.host}:{self.port}{self.__api_path}"

        return f"{self.host}{self.__api_path}"

    def generate_path_to(self, endpoint: str):
        """ Generate URL from host, port and endpoint.

            :param endpoint: endpoint to reach at the server
        """
        if endpoint.startswith('/'):
            path = self.base_path + endpoint
        else:
            path = self.base_path + '/' + endpoint

        # self.log.debug(f"Generated path to {path}")
        return path

    def request(self, endpoint: str, json: dict = None, method: str = 'get',
                params=None, first_try=True):
        """ Create HTTP(S) request to the central server.

            It can contain a payload (JSON) in case of a POST method.

            :param endpoint: endpoint at the server to which the request
                should be send
            :param json: payload to send with the request
            :param method: HTTP method to use
            :param params: additional parameters to sent with the
                request
        """
        assert self._access_token, \
            "Sending a request can only be done after authentication"

        # get appropiate method
        rest_method = {
            'get': requests.get,
            'post': requests.post,
            'put': requests.put,
            'patch': requests.patch,
            'delete': requests.delete
        }.get(method.lower(), requests.get)

        # send request to server
        url = self.generate_path_to(endpoint)
        self.log.debug(f'Making request: {method.upper()} | {url} | {params}')
        response = rest_method(url, json=json, headers=self.headers,
                               params=params)

        # server says no!
        if response.status_code > 210:
            # self.log.debug(f"Server did respond code={response.status_code}\
            #     and message={response.get('msg', 'None')}")
            self.log.error(
                f'Server responded with error code: {response.status_code}')
            self.log.debug(response.json().get("msg", ""))

            if first_try:
                self.refresh_token()
                return self.request(endpoint, json, method, params,
                                    first_try=False)
            else:
                self.log.error("Nope, refreshing the token didn't fix it.")

        # self.log.debug(f"Response data={response.json()}")
        return response.json()

    def setup_encryption(self, private_key_file) -> CryptorBase:
        """ Enable the encryption module for the communcation.

            This will attach a Cryptor object to the server_io. It will
            first check that the public_key stored at the server is the
            same as the one that is locally derived from the private
            key. If this is not the case, the new public key will be
            uploaded to the server.

            :param private_key_file: local path to the private key
            :param disabled: boolean value to indicate that encryption
                is disabled. Only recommended for testing or debugging
                purposes.

            TODO update other parties when a new public_key is posted
            TODO clean up this method can be shorter
        """
        assert self._access_token, \
            "Encryption can only be setup after authentication"
        assert self.whoami.organization_id, \
            "Organization unknown... Did you authenticate?"

        if private_key_file is None:
            self.cryptor = DummyCryptor()
            return

        cryptor = RSACryptor(private_key_file)

        # check if the public-key is the same on the server. If this is
        # not the case, this node will not be able to read any messages
        # that are send to him! If this is the case, the new public_key
        # will be uploaded to the central server
        organization = self.request(
            f"organization/{self.whoami.organization_id}")
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
                json={"public_key": cryptor.public_key_str}
            )
            self.log.info("The public key on the server is updated!")

        self.cryptor = cryptor

    def authenticate(self, credentials: dict, path="token/user"):
        """Authenticate to the central server.

            It allows signin for all identities (user, node, container).
            Therefore credentials can be either a username/password
            combination or a JWT authorization token

            :param credentials: username/password or apikey as a dict
            :param path: path to authentication endpoint. For a user
                this is `token/user`, for a node `token/node` and for
                a container `token/container`.
        """
        self.log.debug(f"Authenticating using {credentials}")

        # authenticate to the central server
        url = self.generate_path_to(path)
        response = requests.post(url, json=credentials)
        data = response.json()

        # handle negative responses
        if response.status_code > 200:
            self.log.critical(f"Failed to authenticate {data.get('msg')}")
            raise Exception("Failed to authenticate")

        # store tokens in object
        self.log.info("Successfully authenticated")
        self._access_token = data.get("access_token")
        self.__refresh_token = data.get("refresh_token")
        self.__refresh_url = data.get("refresh_url")

    def refresh_token(self):
        """ Refresh an expired token.

            TODO create a more helpful Exception
        """

        self.log.info("Refreshing token")
        assert self.__refresh_url, \
            "Refresh URL not found, did you authenticate?"

        # if no port is specified explicit, then it should be omnit the
        # colon : in the path. Similar (but different) to the property
        # base_path
        if self.__port:
            url = f"{self.__host}:{self.__port}{self.__refresh_url}"
        else:
            url = f"{self.__host}{self.__refresh_url}"

        # send request to server
        response = requests.post(url, headers={
            'Authorization': 'Bearer ' + self.__refresh_token
        })

        # server says no!
        if response.status_code != 200:
            self.log.critical("Could not refresh token")
            raise Exception("Authentication Error!")

        self._access_token = response.json()["access_token"]

    def post_task(self, name: str, image: str, collaboration_id: int,
                  input_: bytes = b'', description='',
                  organization_ids: list = None) -> dict:
        """ Post a new task at the server.

            It will also encrypt `input_` for each receiving
            organization.

            :param name: human-readable name of the task
            :param image: docker image name of the task
            :param collaboration_id: id of the collaboration in which
                this task needs to be executed
            :param input_: input for the algorithm
            :param description: human readable description of the task
            :param organization_ids: id's of the organizations that need
                to execute the task
            :param data_format: Type of data format to use to send and receive
                data. possible values: 'json', 'pickle', 'legacy'. 'legacy'
                will use pickle serialization. Default is 'legacy'.
        """
        assert self.cryptor, "Encryption has not yet been setup!"

        if organization_ids is None:
            organization_ids = []

        if data_format == LEGACY:
            serialized_input = pickle.dumps(input_)
        else:
            # Data will be serialized to bytes in the specified data format.
            # It will be prepended with 'DATA_FORMAT.' in unicode.
            serialized_input = data_format.encode() + b'.' \
                + serialization.serialize(input_, data_format)

        organization_json_list = []
        for org_id in organization_ids:
            pub_key = self.request(f"organization/{org_id}").get("public_key")
            # pub_key = base64s_to_bytes(pub_key)
            # self.log.debug(pub_key)

            organization_json_list.append({
                "id": org_id,
                "input": self.cryptor.encrypt_bytes_to_str(serialized_input,
                                                           pub_key)
            })

        return self.request('task', method='post', json={
            "name": name,
            "image": image,
            "collaboration_id": collaboration_id,
            "description": description,
            "organizations": organization_json_list
        })

    def get_results(self, id=None, state=None, include_task=False,
                    task_id=None, node_id=None):
        """Get task result(s) from the central server.

            Depending if a `id` is specified or not, either a single or
            a list of results is returned. The input and result field
            of the result are attempted te be decrypted. This fails if
            the public key at the server is not derived from the
            currently private key.

            :param id: id of the result
            :param state: the state of the task (e.g. `open`)
            :param include_task: whenever to include the orginating task
            :param task_id: the id of the originating task, this will
                return all results belonging to this task
            :param node_id: the id of the node at which this result has
                been produced, this will return all results from this
                node
        """

        def decrypt_result(res):
            """Helper to decrypt the keys 'input' and 'result' in dict.

            Keys are replaced, but object reference remains intact: changes are
            made *in-place*.
            """
            cryptor = self.cryptor
            try:
                self.log.info('Decrypting input')
                # TODO this only works when the results belong to the
                # same organization... We should make different implementation
                # of get_results
                res["input"] = cryptor.decrypt_str_to_bytes(res["input"])

            except Exception as e:
                self.log.debug(e)

            try:
                if res["result"]:
                    self.log.info('Decrypting result')
                    res["result"] = cryptor.decrypt_str_to_bytes(res["result"])

            except ValueError as e:
                self.log.error("Could not decrypt/decode input or result.")
                self.log.error(e)
                # raise

        # Determine endpoint and create dict with query parameters
        endpoint = 'result' if not id else f'result/{id}'
        params = dict()

        if state:
            params['state'] = state
        if include_task:
            params['include'] = 'task'
        if task_id:
            params['task_id'] = task_id
        if node_id:
            params['node_id'] = node_id

        # self.log.debug(f"Retrieving results using query parameters:{params}")
        results = self.request(endpoint=endpoint, params=params)

        if id:
            # Single result
            decrypt_result(results)

        else:
            # Multiple results
            for result in results:
                decrypt_result(result)

        return results


class UserClient(ClientBase):
    """ User interface to the central server."""

    def authenticate(self, username: str, password: str):
        """ User authentication at the central server.

            It also identifies itself by retrieving the organization to
            which this user belongs. The server returns a JWT-token
            that is used in all succeeding requests.

            :param username: username used to authenticate
            :param password: password used to authenticate
        """
        super(UserClient, self).authenticate({
            "username": username,
            "password": password
        }, path="token/user")

        # identify the user and the organization to which this user
        # belongs. This is usefull for some client side checks
        type_ = "user"
        id_ = jwt.decode(self.token, verify=False)['identity']
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
            organization_name=organization_name
        )

    def get_results(self, id=None, state=None, include_task=False,
                    task_id=None, node_id=None):

        results = super().get_results(
            id=id, state=state,
            include_task=include_task, task_id=task_id, node_id=node_id
        )

        unpacked_results = []
        for result in results:
            if result.get("result"):
                result["result"] = deserialization.load_data(
                    result.get('result')
                )
            unpacked_results.append(result)

        return unpacked_results


class ContainerClient(ClientBase):
    """ Container interface to the local proxy server (central server).

        A algorithm container (should) never communicate directly to the
        central server. Therefore the algorithm container has no
        internet connection. The algorithm can, however, talk to a local
        proxy server which has interface to the central server. This way
        we make sure that the algorithm container does not share stuff
        with others, and we also can encrypt the results for a specific
        receiver. Thus this not a interface to the central server but to
        the local proxy server. However the interface is identical thus
        we are happy that we can ignore this detail.
    """

    def __init__(self, token: str, *args, **kwargs):
        """ All permissions of the container are derived from the
            token.

            :param token: JWT (container) token, generated by the node
                the algorithm container runs on
        """
        super().__init__(*args, **kwargs)

        # obtain the identity from the token
        container_identity = jwt.decode(token, verify=False)['identity']
        self.image = container_identity.get("image")
        self.host_node_id = container_identity.get("node_id")
        self.collaboration_id = container_identity.get("collaboration_id")
        self.log.info(
            f"Container in collaboration_id={self.collaboration_id} \n"
            f"Key created by node_id {self.host_node_id} \n"
            f"Can only use image={self.image}"
        )

        self._access_token = token
        self.log.debug(f"Access token={self._access_token}")

    def authenticate(self):
        """ Containers obtain their key via their host Node."""
        self.log.warn("Containers do not authenticate?!")
        return

    def refresh_token(self):
        """ Containers cannot refresh their token.

            TODO we might want to notify node/server about this...
            TODO make a more usefull exception
        """
        raise Exception("Containers cannot refresh!")

    def get_results(self, task_id: int):
        """ Obtain results from a specific task at the server

            Containers are allowed to obtain the results of their
            children (having the same run_id at the server). The
            permissions are checked at te central server.

            :param task_id: id of the task from which you want to obtain
                the results
        """
        results = self.request(
            f"task/{task_id}/result"
        )

        res = [pickle.loads(base64s_to_bytes(result.get("result")))
               for result in results]

        return res

    def get_task(self, task_id: int):
        return self.request(
            f"task/{task_id}"
        )

    def create_new_task(self, input_, organization_ids=[]):
        """ Create a new (child) task at the central server.

            Containers are allowed to create child tasks (having the
            same run_id) at the central server. The docker image must
            be the same as the docker image of this container self.

            :param input_: input to the task
            :param organization_ids: organization ids which need to
                execute this task
        """
        self.log.debug(f"create new task for {organization_ids}")

        return self.post_task(
            name="subtask",
            description=f"task from container on node_id={self.host_node_id}",
            collaboration_id=self.collaboration_id,
            organization_ids=organization_ids,
            input_=input_,
            image=self.image
        )

    def get_organizations_in_my_collaboration(self):
        """ Obtain all organization in the collaboration.

            The container runs in a Node which is part of a single
            collaboration. This method retrieves all organization data
            that are within that collaboration. This can be used to
            target specific organizations in a collaboration.
        """
        organizations = self.request(
            f"collaboration/{self.collaboration_id}/organization")
        return organizations

    def post_task(self, name: str, image: str, collaboration_id: int,
                  input_: str = '', description='',
                  organization_ids: list = []) -> dict:
        """ Post a new task at the central server.

            ! To create a new task from the algorithm container you
            should use the `create_new_task` function !

            Creating a task from a container does need to be encrypted.
            This is done because the container should never have access
            to the private key of this organization. The encryption
            takes place in the local proxy server to which the algorithm
            communicates (indirectly to the central server). Therefore
            we needed to overload the post_task function.

            :param name: human-readable name
            :param image: docker image name of the task
            :param collaboration_id: id of the collaboration in which
                the task should run
            :param input_: input to the task
            :param description: human-readable description
            :param organization_ids: ids of the organizations where this
                task should run
        """
        self.log.debug("post task without encryption (is handled by proxy)")

        serialized_input = bytes_to_base64s(pickle.dumps(input_))

        organization_json_list = []
        for org_id in organization_ids:
            organization_json_list.append(
                {
                    "id": org_id,
                    "input": serialized_input
                }
            )

        return self.request('task', method='post', json={
            "name": name,
            "image": image,
            "collaboration_id": collaboration_id,
            "description": description,
            "organizations": organization_json_list
        })


# For backwards compatibility
ClientContainerProtocol = ContainerClient
Client = UserClient
ClientBaseProtocol = ClientBase
