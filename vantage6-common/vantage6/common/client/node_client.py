"""
This module provides a client interface for the node to communicate with the
central server.
"""

import datetime
import os
import time
from threading import Thread

from keycloak import KeycloakOpenID

from vantage6.common import WhoAmI
from vantage6.common.client.client_base import ClientBase
from vantage6.common.globals import (
    InstanceType,
    RequiredNodeEnvVars,
)


class NodeClient(ClientBase):
    """Node interface to the central server."""

    def __init__(
        self, node_account_name: str, api_key: str, server_url: str, auth_url: str
    ):
        """
        Initialize the node client.

        Parameters
        ----------
        node_account_name : str
            The name of the node account.
        api_key : str
            The api key of the node.
        server_url : str
            The url of the server to connect to.
        auth_url : str
            The url of the authentication server.
        """
        super().__init__(server_url=server_url, auth_url=auth_url)

        self.node_account_name = node_account_name
        self.api_key = api_key

        # self.name = None
        self.collaboration_id = None
        self.whoami = None
        self.keycloak_client_id = None

        self.run = self.Run(self)
        self.algorithm_store = self.AlgorithmStore(self)
        self.column = self.Column(self)

        self.kc_openid = KeycloakOpenID(
            server_url=self.auth_url,
            realm_name=os.environ.get(RequiredNodeEnvVars.KEYCLOAK_REALM.value),
            client_id=f"{self.node_account_name}-node-client",
            client_secret_key=self.api_key,
        )
        self.token_validity_period = None

    def authenticate(self) -> None:
        """
        Nodes authentication by using keycloak.
        """
        # get token from keycloak
        try:
            self.obtain_new_token()
        except Exception as e:
            self.log.exception("Getting token failed: %s", e)
            raise e

        # get info on how the server sees this node
        node = self.request("node/me")

        name = node.get("name")
        self.collaboration_id = node.get("collaboration").get("id")

        organization_id = node.get("organization").get("id")
        organization = self.request(f"organization/{organization_id}")
        organization_name = organization.get("name")

        self.whoami = WhoAmI(
            type_=InstanceType.NODE.value,
            id_=node["id"],
            name=name,
            organization_id=organization_id,
            organization_name=organization_name,
        )

    def obtain_new_token(self) -> None:
        """Get a new token."""
        self.log.debug("Obtaining new token")
        token = self.kc_openid.token(grant_type="client_credentials")
        self._access_token = token["access_token"]
        decoded_token = self.kc_openid.decode_token(self._access_token)
        self.token_validity_period = decoded_token["exp"] - decoded_token["iat"]

    def auto_renew_token(self) -> None:
        """Start a thread that refreshes token before it expires."""
        # set up thread to refresh token
        t = Thread(target=self.__renew_token_worker, daemon=True)
        t.start()

    def __renew_token_worker(self) -> None:
        """Keep refreshing token to prevent it from expiring."""
        # set variable to start trying to refresh the token 3/4 of the time before
        # it expires
        period_start_refresh = self.token_validity_period / 4
        # set variable to sleep between refreshes - so that we have about 20 attempts
        # before the token expires
        interval_between_refreshes = period_start_refresh / 20
        token_expired = False
        while True:
            # get the time until the token expires
            expiry_time = self.kc_openid.decode_token(self.token)["exp"]
            time_until_expiry = expiry_time - time.time()
            if time_until_expiry < period_start_refresh:
                if time_until_expiry < 0 and not token_expired:
                    token_expired = True
                    self.log.error("Token has expired. Some requests may have failed!")
                    # if token expires, keycloak service is down, or internet connection
                    # of the node is down. We keep on trying to refresh the token but
                    # not too often.
                    interval_between_refreshes = 60  # 1 minute
                try:
                    self.obtain_new_token()
                    token_expired = False
                except Exception as e:
                    self.log.error("Getting new token failed: %s", e)
                    # sleep for a bit and then try again. The server might be
                    # unreachable or internet connection down. We sleep so long that
                    # we should have about 20 attempts before the token expires.
                    time.sleep(interval_between_refreshes)
            else:
                time.sleep(int(time_until_expiry - period_start_refresh + 1))

    def request_token_for_container(self, task_id: int, image: str) -> dict:
        """Request a container-token at the central server.

        This token is used by algorithm containers that run on this
        node. These algorithms can then create subtasks and retrieve
        subresults.

        The server performs a few checks (e.g. if the task you
        request the key for is in progress) before handing out this
        token.

        Parameters
        ----------
        task_id : int
            id from the task, which is going to use this container token
        image : str
            Docker image name of the task

        Returns
        -------
        dict
            The container token.
        """
        self.log.debug(
            "Requesting container token for task_id=%s and image=%s", task_id, image
        )
        return self.request(
            "/token/container", method="post", json={"task_id": task_id, "image": image}
        )

    class Run(ClientBase.SubClient):
        """Subclient for the run endpoint."""

        def list(
            self, state: str, include_task: bool, task_id: int = None
        ) -> dict | list:
            """
            Obtain algorithm runs.

            Parameters
            ----------
            state : str
                State of the desired algorithm runs.
            include_task : bool, optional
                Include the task
            task_id : int, optional
                ID of the task, by default None. If None, all tasks are
                returned.

            Returns
            -------
            dict | list
                The algorithm runs as json.
            """
            params = {"state": state, "node_id": self.parent.whoami.id_}
            if include_task:
                params["include"] = "task"
            if task_id:
                params["task_id"] = task_id
            run_data = self.parent.request(endpoint="run", params=params)

            if isinstance(run_data, str):
                self.parent.log.warning("Requesting algorithm runs failed")
                self.parent.log.warning(f"Fail message: {run_data}")
                return {}

            # if there are multiple pages of algorithm runs, get them all
            links = run_data.get("links")

            page = 1
            while links and links.get("next"):
                page += 1
                next_page = self.parent.request(
                    endpoint="run", params={**params, "page": page}
                )
                run_data["data"] += next_page["data"]
                links = next_page.get("links")

            # strip pagination links
            run_data = run_data["data"]

            # Multiple runs
            for run in run_data:
                run["arguments"] = self.parent._decrypt_data(run["arguments"])

            return run_data

        def patch(self, id_: int, data: dict, init_org_id: int = None) -> dict | None:
            """
            Update the algorithm run data at the central server.

            Typically used for task status updates (started, finished, etc)

            Parameters
            ----------
            id_: int
                ID of the run to patch
            data: Dict
                Dictionary of fields that are to be patched
            init_org_id: int, optional
                Organization id of the origin of the task. This is required
                when the run dict includes results, because then results have
                to be encrypted specifically for them

            Returns
            -------
            dict | None
                The response from the server, or None if wrong data was provided
            """
            if "result" in data:
                if not init_org_id:
                    self.parent.log.critical(
                        "Organization id is not provided: cannot send results "
                        "to server as they cannot be encrypted"
                    )
                    return
                self.parent.log.debug(
                    f"Retrieving public key from organization={init_org_id}"
                )

                org = self.parent.request(f"organization/{init_org_id}")
                public_key = None
                try:
                    public_key = org["public_key"]
                except KeyError:
                    self.parent.log.critical(
                        "Public key could not be retrieved... Does the "
                        "initiating organization belong to your organization?"
                    )

                data["result"] = self.parent.cryptor.encrypt_bytes_to_str(
                    data["result"], public_key
                )

            self.parent.log.debug("Sending algorithm run update to server")
            return self.parent.request(f"run/{id_}", json=data, method="patch")

    class AlgorithmStore(ClientBase.SubClient):
        """Subclient for the algorithm store endpoint."""

        def get(self, id_) -> dict:
            """
            Obtain algorithm store from the central server.

            Parameters
            ----------
            id_ : int
                ID of the algorithm.

            Returns
            -------
            dict
                The algorithms as json.
            """
            return self.parent.request(f"algorithmstore/{id_}")

    class Column(ClientBase.SubClient):
        """Subclient for the column endpoint."""

        def post(self, df_id: int, data: dict) -> dict:
            """
            Create a column at the central server.

            Parameters
            ----------
            df_id: int
                ID of the dataframe.
            data: dict
                Dictionary of fields that are to be patched

            Returns
            -------
            dict
                The response from the server.
            """
            return self.parent.request(
                f"session/dataframe/{df_id}/column", method="post", json=data
            )

    def is_encrypted_collaboration(self) -> bool:
        """
        Check whether the encryption is enabled.

        End-to-end encryption is per collaboration managed at the
        central server. It is important to note that the local
        configuration-file should allow explicitly for unencrpyted
        messages. This function returns the setting from the server.

        Returns
        -------
        bool
            True if the collaboration is encrypted, False otherwise.
        """
        response = self.request(f"collaboration/{self.collaboration_id}")
        return response.get("encrypted") == 1

    def set_run_start_time(self, id_: int) -> None:
        """
        Sets the start time of the task at the central server.

        This is important as this will note that the task has been
        started, and is waiting for restuls.

        Parameters
        ----------
        id_ : int
            ID of the task.
        """
        self.run.patch(
            id_,
            data={
                "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            },
        )

    def check_user_allowed_to_send_task(
        self,
        allowed_users: list[str],
        allowed_orgs: list[str],
        init_org_id: int,
        init_user_id: int,
    ) -> bool:
        """
        Check if the user is allowed to send a task to this node

        Parameters
        ----------
        allowed_users: list[str]
            List of allowed user IDs or usernames
        allowed_orgs: list[str]
            List of allowed organization IDs or names
        init_org_id: int
            ID of the organization that initiated the task
        init_user_id: int
            ID of the user that initiated the task

        Returns
        -------
        bool
            Whether or not the user is allowed to send a task to this node
        """
        # check if task-initating user id is in allowed users
        if any(str(init_user_id) == user for user in allowed_users):
            return True

        # check if task-initiating org id is in allowed orgs
        if any(str(init_org_id) == org for org in allowed_orgs):
            return True

        # TODO it would be nicer to check all users in a single request
        # but that requires other multi-filter options in the API
        # TODO this option is now disabled since nodes do not have permission
        # to access user information. We need to decide if we want to give them
        # that permission for this.
        # ----------------------------------------------------------
        # check if task-initiating user name is in allowed users
        # for user in allowed_users:
        #     resp = self.request("user", params={"username": user})
        #     print(resp)
        #     for d in resp:
        #         if d.get("username") == user and d.get("id") == init_user_id:
        #             return True

        # check if task-initiating org name is in allowed orgs
        for allowed_org in allowed_orgs:
            resp = self.request("organization", params={"name": allowed_org})
            for org in resp:
                if org.get("name") == allowed_org and org.get("id") == init_org_id:
                    return True

        # not in any of the allowed users or orgs
        return False
