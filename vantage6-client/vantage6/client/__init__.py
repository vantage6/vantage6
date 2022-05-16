"""
vantage6 clients

This module is contains a base client. From this base client the container
client (client used by master algorithms) and the user client are derived.
"""
import logging
import pickle
import time
import typing
import jwt
import requests
import pyfiglet
import json as json_lib

from pathlib import Path

from vantage6.common import bytes_to_base64s, base64s_to_bytes
from vantage6.common.globals import APPNAME
from vantage6.client import serialization, deserialization
from vantage6.client.filter import post_filtering
from vantage6.client.encryption import RSACryptor, DummyCryptor


module_name = __name__.split('.')[1]

LEGACY = 'legacy'


class ServerInfo(typing.NamedTuple):
    """Data-class to store the server info."""
    host: str
    port: int
    path: str


class WhoAmI(typing.NamedTuple):
    """ Data-class to store Authenticable information in."""
    type_: str
    id_: int
    name: str
    organization_name: str
    organization_id: int

    def __repr__(self) -> str:
        return (f"<WhoAmI "
                f"name={self.name}, "
                f"type={self.type_}, "
                f"organization={self.organization_name}, "
                f"(id={self.organization_id})"
                ">")


class ClientBase(object):
    """Common interface to the central server.

    Contains the basis for all other clients. This includes a basic interface
    to authenticate, generic request, creating tasks and result retrieval.
    """

    def __init__(self, host: str, port: int, path: str = '/api'):
        """Basic setup for the client

        Parameters
        ----------
        host : str
            Adress (including protocol, e.g. `https://`) of the vantage6 server
        port : int
            port numer to which the server listens
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
        """Return the node's/client's name"""
        return self.whoami.name

    @property
    def headers(self) -> dict:
        """Headers that are send with each request"""
        if self._access_token:
            return {'Authorization': 'Bearer ' + self._access_token}
        else:
            return {}

    @property
    def token(self) -> str:
        """JWT Authorization token"""
        return self._access_token

    @property
    def host(self) -> str:
        """Host including protocol (HTTP/HTTPS)"""
        return self.__host

    @property
    def port(self) -> int:
        """Port to vantage6-server listens"""
        return self.__port

    @property
    def path(self) -> str:
        """Path/endpoint at the server where the api resides"""
        return self.__api_path

    @property
    def base_path(self) -> str:
        """Combination of host, port and api-path"""
        if self.__port:
            return f"{self.host}:{self.port}{self.__api_path}"

        return f"{self.host}{self.__api_path}"

    def generate_path_to(self, endpoint: str) -> str:
        """Generate URL to endpoint using host, port and endpoint

        Parameters
        ----------
        endpoint : str
            endpoint to which a fullpath needs to be generated

        Returns
        -------
        str
            URL to the endpoint
        """
        if endpoint.startswith('/'):
            path = self.base_path + endpoint
        else:
            path = self.base_path + '/' + endpoint

        return path

    def request(self, endpoint: str, json: dict = None, method: str = 'get',
                params: dict=None, first_try: bool=True) -> dict:
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
        first_try : bool, optional
            Whenever this is the first attemt of this request, by default True

        Returns
        -------
        dict
            Eesponse of the server
        """

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

        try:
            response = rest_method(url, json=json, headers=self.headers,
                                   params=params)
        except requests.exceptions.ConnectionError as e:
            # we can safely retry as this is a connection error. And we
            # keep trying!
            self.log.error('Connection error... Retrying')
            self.log.debug(e)
            time.sleep(1)
            return self.request(endpoint, json, method, params)

        # TODO: should check for a non 2xx response
        if response.status_code > 210:
            self.log.error(
                    f'Server responded with error code: {response.status_code}')
            try:
                self.log.error("msg:"+response.json().get("msg", ""))
            except json_lib.JSONDecodeError:
                self.log.error('Did not find a message from the server')
                self.log.debug(response.content)

            if first_try:
                self.refresh_token()
                return self.request(endpoint, json, method, params,
                                    first_try=False)
            else:
                self.log.error("Nope, refreshing the token didn't fix it.")

        return response.json()

    def setup_encryption(self, private_key_file: str) -> None:
        """Enable the encryption module fot the communication

        This will attach a Crypter object to the client. It will also
        verify that the public key at the server matches the local
        private key. In case they differ, the local public key is uploaded
        to the server.

        Parameters
        ----------
        private_key_file : str
            File path of the private key file

        """
        assert self._access_token, \
            "Encryption can only be setup after authentication"
        assert self.whoami.organization_id, \
            "Organization unknown... Did you authenticate?"

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

    def authenticate(self, credentials: dict, path: str="token/user") -> None:
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

    def refresh_token(self) -> None:
        """Refresh an expired token using the refresh token

        Raises
        ------
        Exception
            Authentication Error!
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
                  input_='', description='',
                  organization_ids: list = None,
                  data_format=LEGACY, database: str='default') -> dict:
        """Post a new task at the server

        It will also encrypt `input_` for each receiving organization.

        Parameters
        ----------
        name : str
            Human readable name for the task
        image : str
            Docker image name containing the algorithm
        collaboration_id : int
            Collaboration `id` of the collaboration for which the task is
            intended
        input_ : str, optional
            Task input, by default ''
        description : str, optional
            Human readable description of the task, by default ''
        organization_ids : list, optional
            Ids of organizations (within the collaboration) that need to
            execute this task, by default None
        data_format : str, optional
            Type of data format to use to send and receive
            data. possible values: 'json', 'pickle', 'legacy'. 'legacy'
            will use pickle serialization. Default is 'legacy'., by default
            LEGACY

        Returns
        -------
        dict
            Containing the task meta-data
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
                "input": self.cryptor.encrypt_bytes_to_str(serialized_input, pub_key)
            })

        return self.request('task', method='post', json={
            "name": name,
            "image": image,
            "collaboration_id": collaboration_id,
            "description": description,
            "organizations": organization_json_list,
            'database': database
        })

    def get_results(self, id: int=None, state: str=None,
                    include_task: bool=False, task_id: int=None,
                    node_id: int=None) -> dict:
        """Get task result(s) from the central server

        Depending if a `id` is specified or not, either a single or a
        list of results is returned. The input and result field of the
        result are attempted te be decrypted. This fails if the public
        key at the server is not derived from the currently private key
        or when the result is not from your organization.

        Parameters
        ----------
        id : int, optional
            Id of the result, by default None
        state : str, optional
            The state of the task (e.g. `open`), by default None
        include_task : bool, optional
            Whenever to include the orginating task, by default False
        task_id : int, optional
            The id of the originating task, this will return all results
            belonging to this task, by default None
        node_id : int, optional
            The id of the node at which this result has been produced,
            this will return all results from this node, by default None

        Returns
        -------
        dict
            Containing the result(s)
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

    class SubClient:
        """Create sub groups of commands using this SubClient"""
        def __init__(self, parent):
                self.parent = parent


class UserClient(ClientBase):
    """User interface to the vantage6-server"""

    def __init__(self, *args, verbose=False, **kwargs):
        """Create user client

        All paramters from `ClientBase` can be used here.

        Parameters
        ----------
        verbose : bool, optional
            Whenever to print (info) messages, by default False
        """
        super(UserClient, self).__init__(*args, **kwargs)

        # Replace logger by print logger
        self.log = self.Log(verbose)

        # attach sub-clients
        self.util = self.Util(self)
        self.collaboration = self.Collaboration(self)
        self.organization = self.Organization(self)
        self.user = self.User(self)
        self.result = self.Result(self)
        self.task = self.Task(self)
        self.role = self.Role(self)
        self.node = self.Node(self)
        self.rule = self.Rule(self)

        # Display welcome message
        self.log.info(" Welcome to")
        for line in pyfiglet.figlet_format(APPNAME, font='big').split('\n'):
            self.log.info(line)
        self.log.info(" --> Join us on Discord! https://discord.gg/rwRvwyK")
        self.log.info(" --> Docs: https://docs.vantage6.ai")
        self.log.info(" --> Blog: https://vantage6.ai")
        self.log.info("-" * 45)

    class Log:
        """Replaces the default logging meganism by print statements"""
        def __init__(self, enabled: bool):
            """Create print-logger

            Parameters
            ----------
            enabled : bool
                Whenever to enable logging
            """
            self.enabled = enabled
            for level in ['debug', 'info', 'warn', 'warning', 'error',
                          'critical']:
                self.__setattr__(level, self.print)

        def print(self, msg: str) -> None:
            if self.enabled:
                print(f'{msg}')

    def authenticate(self, username: str, password: str) -> None:
        """Authenticate as a user

        It also collects some additional info about your user.

        Parameters
        ----------
        username : str
            Username used to authenticate
        password : str
            Password used to authenticate
        """
        super(UserClient, self).authenticate({
            "username": username,
            "password": password
        }, path="token/user")

        # identify the user and the organization to which this user
        # belongs. This is usefull for some client side checks
        try:
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

            self.log.info(f" --> Succesfully authenticated")
            self.log.info(f" --> Name: {name} (id={id_})")
            self.log.info(f" --> Organization: {organization_name} (id={organization_id})")
        except Exception as e:
            self.log.info(f'--> Retrieving additional user info failed!')
            self.log.debug(e)

    class Util(ClientBase.SubClient):
        """Collection of general utilities"""

        def get_server_version(self) -> dict:
            r"""View the version number of the vantage6-server

            Returns
            -------
            dict
                A dict containing the version number
            """
            return self.parent.request('version')

        def get_server_health(self) -> dict:
            """View the health of the vantage6-server

            Returns
            -------
            dict
                Containing the server health information
            """
            return self.parent.request('health')

        def reset_my_password(self, email: str=None, username: str=None) -> dict:
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
            assert email or username, "You need to provide username or email!"
            result = self.parent.request('recover/lost', method='post', json={
                'username': username,
                'email': email
            })
            msg = result.get('msg')
            self.parent.log.info(f'--> {msg}')
            return result

        def set_my_password(self, token: str, password: str) -> dict:
            """Set a new password using a recovery token

            Token kan be obtained through `.reset_password(...)`

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
            result = self.parent.request('recover/reset', method='post', json={
                'reset_token': token,
                'password': password
            })
            msg = result.get('msg')
            self.parent.log.info(f'--> {msg}')
            return result

        def generate_private_key(self, file_: str=None) -> None:
            """Generate new private key

            ....

            Parameters
            ----------
            file_ : str, optional
                Path where to store the private key, by default None
            """

            if not file_:
                self.parent.log.info('--> Using current directory')
                file_ = "private_key.pem"

            if isinstance(file_, str):
                file_ = Path(file_).absolute()

            self.parent.log.info(f'--> Generating private key file: {file_}')
            private_key = RSACryptor.create_new_rsa_key(file_)

            self.parent.log.info('--> Assigning private key to client')
            self.parent.cryptor.private_key = private_key

            self.parent.log.info('--> Encrypting the client and uploading '
                                 'the public key')
            self.parent.setup_encryption(file_)

    class Collaboration(ClientBase.SubClient):
        """Collection of collaboration requests"""

        @post_filtering()
        def list(self, scope: str='organization') -> dict:
            """View your collaborations

            Parameters
            ----------
            scope : str
                Scope of the list, accepted values are `organization` and
                `global`. In case of `organization` you get the collaborations
                in which your organization participates. If you specify global
                you get the collaborations which you are allowed to see.

            Returns
            -------
            list of dicts
                Containing collabotation information
            """
            if scope == 'organization':
                org_id = self.parent.whoami.organization_id
                return self.parent.request(f'organization/{org_id}/collaboration')
            elif scope == 'global':
                return self.parent.request(f'collaboration')
            else:
                self.parent.log.info('--> Unrecognized `scope`. Need to be '
                                     '`organization` or `global`')

        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific collaboration

            Parameters
            ----------
            id_ : int
                Id from the collaboration you want to view

            Returns
            -------
            dict
                Containing the collaboration information
            """
            return self.parent.request(f'collaboration/{id_}')

        @post_filtering(iterable=False)
        def create(self, name: str, organizations: list,
                   encrypted: bool=False) -> dict:
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

            Returns
            -------
            dict
                Containing the new collaboration meta-data
            """
            return self.parent.request('collaboration', method='post', json={
                'name': name,
                'organization_ids': organizations,
                'encrypted': encrypted
            })

    class Node(ClientBase.SubClient):
        """Collection of node requests"""

        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific node

            Parameters
            ----------
            id_ : int
                Id of the node you want to inspect

            Returns
            -------
            dict
                Containing the node meta-data
            """
            return self.parent.request(f'node/{id_}')

        @post_filtering()
        def list(self) -> list:
            """List nodes

            Returns
            -------
            list of dicts
                Containing meta-data of the nodes
            """
            return self.parent.request('node')

        @post_filtering(iterable=False)
        def create(self, collaboration: int, organization: int=None) -> dict:
            """Register new node

            Parameters
            ----------
            collaboration : int
                Collaboration id to which this node belongs
            organization : int, optional
                Organization id to which this node belongs. If no id provided
                the users organization is used. By default None

            Returns
            -------
            dict
                Containing the meta-data of the new node
            """
            if not organization:
                organization = self.parent.whoami.organization_id

            return self.parent.request('node', method='post', json={
                'organization_id': organization,
                'collaboration_id': collaboration
            })

        @post_filtering(iterable=False)
        def update(self, id_: int, name: str=None, organization: int=None,
                   collaboration: int=None) -> dict:
            """Update node information

            Parameters
            ----------
            id_ : int
                Id of the node you want to update
            name : str, optional
                New node name, by default None
            organization : int, optional
                Change the owning organization of the node, by default
                None
            collaboration : int, optional
                Changes the collaboration to which the node belongs, by
                default None

            Returns
            -------
            dict
                Containing the meta-data of the updated node
            """
            return self.parent.request(f'node/{id_}', method='patch', json={
                'name': name,
                'organization_id': organization,
                'collaboration_id': collaboration
            })

        def delete(self, id_: int) -> dict:
            """Deletes a node

            Parameters
            ----------
            id_ : int
                Id of the node you want to delete

            Returns
            -------
            dict
                Message from the server
            """
            return self.parent.request(f'node/{id_}', method='delete')

    class Organization(ClientBase.SubClient):
        """Collection of organization requests"""

        @post_filtering()
        def list(self) -> list:
            """List of organizations

            Returns
            -------
            list of dicts
                Containing meta-data information of the organizations
            """
            return self.parent.request(f'organization')

        @post_filtering(iterable=False)
        def get(self, id_: int=None) -> dict:
            """View specific organization

            Parameters
            ----------
            id_ : int, optional
                Organization `id` of the organization you want to view.
                In case no `id` is profided it will display your own
                organization, default value is None.

            Returns
            -------
            dict
                Containing the organization meta-data
            """
            if not id_:
                id_ = self.parent.whoami.organization_id

            return self.parent.request(f'organization/{id_}')

        @post_filtering(iterable=False)
        def update(self, id_:int=None, name: str=None, address1: str=None,
                   address2: str=None, zipcode: str=None, country: str=None,
                   domain: str=None, public_key: str=None) -> dict:
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

            Returns
            -------
            dict
                The meta-data of the updated organization
            """
            if not id_:
                id_ = self.parent.whoami.organization_id

            return self.parent.request(
                f'organization/{id_}',
                method='patch',
                json={
                    'name': name,
                    'address1': address1,
                    'address2': address2,
                    'zipcode': zipcode,
                    'country': country,
                    'domain': domain,
                    'public_key': public_key
                }
            )

        def create(self, name: str, address1: str, address2: str, zipcode: str,
                   country: str, domain: str, public_key: str=None) -> dict:
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

            Returns
            -------
            dict
                Containing the information of the new organization
            """
            json_data = {
                'name': name,
                'address1': address1,
                'address2': address2,
                'zipcode': zipcode,
                'country': country,
                'domain': domain,
            }

            if public_key:
                json_data['public_key'] = public_key

            return self.parent.request(
                'organization',
                method='post',
                json=json_data
            )

    class User(ClientBase.SubClient):

        @post_filtering()
        def list(self) -> list:
            """List of users

            Returns
            -------
            list of dicts
                Containing the meta-data of the users
            """
            return self.parent.request('user')

        @post_filtering(iterable=False)
        def get(self, id_: int=None) -> dict:
            """View user information

            Parameters
            ----------
            id_ : int, optional
                User `id`, by default None. When no `id` is provided
                your own user information is displayed

            Returns
            -------
            dict
                Containing user information
            """
            if not id_:
                id_ = self.parent.whoami.id_
            return self.parent.request(f'user/{id_}')

        @post_filtering(iterable=False)
        def update(self, id_: int=None, firstname: str=None,
                   lastname: str=None, password: str=None,
                   organization: int=None, rules: list=None,
                   roles: list=None, email: str=None) -> dict:
            """Update user details

            In case you do not supply a user_id, your user is being
            updated.

            Parameters
            ----------
            user_id : int
                User `id` from the user you want to update
            firstname : str
                Your first name
            lastname : str
                Your last name
            password : str
                The password you use to login
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

            Returns
            -------
            dict
                A dict containing the updated user data
            """
            if not id_:
                id_ = self.parent.whoami.id_

            json_body = {
                "firstname": firstname,
                "lastname": lastname,
                "password": password,
                "organization_id": organization,
                "rules": rules,
                "roles": roles,
                "email": email
            }

            # only submit supplied keys
            json_body = {k: v for k, v in json_body.items() if v is not None}

            user = self.parent.request(f'user/{id_}', method='patch',
                                       json=json_body)
            return user

        @post_filtering(iterable=False)
        def create(self, username: str, firstname: str, lastname: str,
                   password: str, email: str, organization: int=None,
                   roles: list=[], rules: list=[]) -> dict:
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
            organization : int
                Organization `id` this user should belong to
            roles : list of ints
                Role ids that are assigned to this user. Note that you
                can only assign roles if you own the rules within this
                role.
            rules : list of ints
                Rule ids that are assigned to this user. Note that you
                can only assign rules that you own

            Return
            ----------
            dict
                Containing data of the new user
            """
            user_data = {
                'username': username,
                'firstname': firstname,
                'lastname': lastname,
                'password': password,
                'email': email,
                'organization_id': organization,
                'roles': roles,
                'rules': rules
            }
            return self.parent.request('user', json=user_data, method='post')

    class Role(ClientBase.SubClient):

        @post_filtering()
        def list(self) -> list:
            """List of roles

            Returns
            -------
            list of dicts
                Containing roles meta-data
            """
            return self.parent.request('role')

        @post_filtering(iterable=True)
        def get(self, id_: int) -> dict:
            """View specific role

            Parameters
            ----------
            id_ : int
                Id of the role you want to insepct

            Returns
            -------
            dict
                Containing meta-data of the role
            """
            return self.parent.request(f'role/{id_}')

        @post_filtering(iterable=True)
        def create(self, name: str, description: str, rules: list,
                   organization: int=None) -> dict:
            """Register new role

            Parameters
            ----------
            name : str
                Role name
            description : str
                Human readable description of the role
            rules : list
                Rules that this role contains
            organization : int, optional
                Organization to which this role belongs. In case this is
                not provided the users organization is used. By default
                None

            Returns
            -------
            dict
                Containing meta-data of the new role
            """
            if not organization:
                organization = self.parent.whoami.organization_id
            return self.parent.request('role', method='post', json={
                'name': name,
                'description': description,
                'rules': rules,
                'organization_id': organization
            })

        @post_filtering(iterable=True)
        def update(self, role: int, name: str=None, description: str=None,
                   rules: list=None) -> dict:
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

            Returns
            -------
            dict
                Containing the updated role data
            """
            return self.parent.request(f'role/{role}', method='patch', json={
                'name': name,
                'description': description,
                'rules': rules
            })

        def delete(self, role: int) -> dict:
            """Delete role

            Parameters
            ----------
            role : int
                CAUTION! Id of the role to be deleted. If you remove
                roles that are attached to you, you might lose access!

            Returns
            -------
            dict
                Message from the server
            """
            res = self.parent.request(f'role/{role}', method='delete')
            self.parent.log.info(f'--> {res.get("msg")}')

    class Task(ClientBase.SubClient):

        @post_filtering(iterable=False)
        def get(self, id_: int, include_results: bool=False) -> dict:
            """View specific task

            Parameters
            ----------
            id_ : int
                Id of the task you want to view
            include_results : bool, optional
                Whenever to include the results or not, by default False

            Returns
            -------
            dict
                Containing the task data
            """
            params = {}
            params['include'] = 'results' if include_results else None
            return self.parent.request(f'task/{id_}', params=params)

        @post_filtering()
        def list(self, include_results: bool=False) -> list:
            """List tasks

            Parameters
            ----------
            include_results : bool, optional
                Whenever to include the results in the tasks, by default
                False

            Returns
            -------
            list of dicts
                Containing data of the tasks
            """
            params = {}
            params['include'] = 'results' if include_results else None
            return self.parent.request('task', params=params)

        @post_filtering(iterable=False)
        def create(self, collaboration: int, organizations: list, name: str,
                   image: str, description: str, input: dict,
                   data_format: str=LEGACY, database: str='default') -> dict:
            """Create a new task

            Parameters
            ----------
            collaboration : int
                Id of the collaboration to which this task belongs
            organizations : list
                Organization ids (within the collaboration) which need
                to execute this task
            name : str
                Human readable name
            image : str
                Docker image name which contains the algorithm
            description : str
                Human readable description
            input : dict
                Algorithm input
            data_format : str, optional
                IO data format used, by default LEGACY
            database: str, optional
                Name of the database to use. This should match the key
                in the node configuration files. If not specified the
                default database will be tried.

            Returns
            -------
            dict
                Containing the task information
            """
            return self.parent.post_task(name, image, collaboration, input,
                                         description, organizations,
                                         data_format, database)

        def delete(self, id_: int) -> dict:
            """Delete a task

            Also removes the related results.

            Parameters
            ----------
            id_ : int
                Id of the task to be removed

            Returns
            -------
            dict
                Message from the server
            """
            msg = self.parent.request(f'task/{id_}', method='delete')
            self.parent.log.info(f'--> {msg}')

    class Result(ClientBase.SubClient):

        @post_filtering(iterable=False)
        def get(self, id_: int, include_task: bool=False) -> dict:
            """View a specific result

            Parameters
            ----------
            id_ : int
                id of the result you want to inspect
            include_task : bool, optional
                Whenever to include the task or not, by default False

            Returns
            -------
            dict
                Containing the result data
            """
            self.parent.log.info('--> Attempting to decrypt results!')

            # get_results also handles decryption
            result = self.parent.get_results(id=id_, include_task=include_task)
            result_data = result.get('result')
            if result_data:
                try:
                    result['result'] = deserialization.load_data(result_data)
                except Exception as e:
                    self.parent.log.warn('--> Failed to deserialize')
                    self.parent.log.debug(e)

            return result

        @post_filtering()
        def list(self, include_task: bool=False) -> list:
            """List results

            Parameters
            ----------
            include_task : bool, optional
                Whenever to include the task or not, by default False

            Returns
            -------
            list of dicts
                Containing the results data
            """
            results = self.parent.get_results(include_task=include_task)
            cleaned_results = []
            for result in results:
                if result.get('result'):
                    try:
                        des_res = deserialization.load_data(result.get('result'))
                    except Exception as e:
                        id_ = result.get('id')
                        self.parent.log.warn(f'Could not deserialize result id='
                                             f'{id_}')
                        self.parent.log.debug(e)
                        continue
                    result['result'] = des_res
                cleaned_results.append(result)

            return cleaned_results

        def from_task(self, task_id: int, include_task: bool=False):
            self.parent.log.info('--> Attempting to decrypt results!')

            # get_results also handles decryption
            results = self.parent.get_results(task_id=task_id,
                                             include_task=include_task)
            cleaned_results = []
            for result in results:
                if result.get('result'):
                    des_res = deserialization.load_data(result.get('result'))
                    result['result'] = des_res
                cleaned_results.append(result)

            return cleaned_results

    class Rule(ClientBase.SubClient):

        @post_filtering(iterable=False)
        def get(self, id_: int) -> dict:
            """View specific rule

            Parameters
            ----------
            id_ : int
                Id of the rule you want to view

            Returns
            -------
            dict
                Containing the information about this rule
            """
            return self.parent.request(f'rule/{id_}')

        @post_filtering()
        def list(self) -> list:
            """List of all available rules

            Returns
            -------
            list of dicts
                Containing all the rules from the vantage6 server
            """
            return self.parent.request('rule')

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
        """Container client.
        A client which can be used by algorithms. All permissions of the container are
        derived from the token.

        Parameters
        ----------
        token : str
            JWT (container) token, generated by the node
                the algorithm container runs on
        """
        super().__init__(*args, **kwargs)

        # obtain the identity from the token
        container_identity = jwt.decode(token, verify=False)['identity']
        self.image = container_identity.get("image")
        self.database = container_identity.get('database')
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
            image=self.image,
            database=self.database
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
                  organization_ids: list = [], database='default') -> dict:
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
            "organizations": organization_json_list,
            "database": database
        })


# For backwards compatibility
ClientContainerProtocol = ContainerClient
Client = UserClient
ClientBaseProtocol = ClientBase
