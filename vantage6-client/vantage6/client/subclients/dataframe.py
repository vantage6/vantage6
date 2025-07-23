from vantage6.common.serialization import serialize
from vantage6.client import ClientBase
from vantage6.client.filter import post_filtering
from vantage6.client.rich.table import rich_dataframe_table, rich_dataframe_schema_table


class DataFrameSubClient(ClientBase.SubClient):
    """Sub client dataframes."""

    @post_filtering(iterable=False)
    def get(self, id_: int, display=False) -> dict:
        """
        Get a dataframe by its ID.

        Parameters
        ----------
        id_ : int
            The ID of the dataframe.
        display : bool, optional
            Whether to print the dataframe details. By default False.

        Returns
        -------
        dict
            The dataframe details.
        """
        df = self.parent.request(f"session/dataframe/{id_}")
        if display:
            rich_dataframe_table(df)
            rich_dataframe_schema_table(df)

        return df

    @post_filtering()
    def list(self, session: int = None, display=False) -> dict:
        """
        List all dataframes.

        Parameters
        ----------
        session : int, optional
            The session ID in which the dataframe is located. When not provided, the
            session ID of the client is used when it is set. In case the session ID is
            not set, an error is printed.
        display : bool, optional
            Whether to print the list of dataframe details. By default False.

        Returns
        -------
        dict
            List of dataframe details.
        """
        session_id = session or self.parent.session_id

        if not session_id:
            self.parent.log.error(
                "No session ID provided and no session ID set in the client."
            )
            return

        dfs = self.parent.request(f"session/{session_id}/dataframe")
        if display:
            rich_dataframe_table(dfs["data"])

        return dfs

    @post_filtering(iterable=False)
    def create(
        self,
        label: str,
        image: str,
        method: str,
        arguments: dict,
        session: int | None = None,
        store: int | None = None,
        name: str | None = None,
        display=False,
    ) -> dict:
        """
        Create a new dataframe in a session.

        Parameters
        ----------
        label : str
            Database label that is specified in the node configuration file.
        image : str
            The name of the image that will be used to retrieve the data from the
            source database.
        method: str
            The method from the algorithm's image to be used for creating the dataframe
        arguments: dict
            Arguments for the algorithm method. The dictionary should contain
            the same keys as the arguments of the algorithm method.
        name: str
            Name that can be used in within the session
        session : int, optional
            The session ID in which the dataframe is located. When not provided, the
            session ID of the client is used when it is set. In case the session ID is
            not set, an error is printed.
        store: int, optional
            The algorithm store where the algorithm image is registered
        display : bool, optional
            Whether to print the dataframe details. By default False.

        Returns
        -------
        dict
            The dataframe details.
        """

        session_id = session or self.parent.session_id
        if not session_id:
            self.parent.log.error(
                "No session ID provided and no session ID set in the client."
            )
            return

        # Get the organizations that are part of the session.
        session = self.parent.request(f"session/{session_id}")
        if not session:
            self.parent.log.error(
                f"An error occurred while fetching session {session_id}"
            )
            return

        if session.get("study"):
            study_id = session["study"]["id"]
            params = {"study": study_id}
        else:
            collaboration_id = session["collaboration"]["id"]
            params = {"collaboration": collaboration_id}

        orgs = self.parent.organization.list(**params)
        organizations = [(o["id"], o["public_key"]) for o in orgs["data"]]

        serialized_arguments = serialize(arguments)

        # Encrypt the input arguments per organization using that organization's
        # public key.
        organization_json_list = []
        for org_id, pub_key in organizations:
            organization_json_list.append(
                {
                    "id": org_id,
                    "arguments": self.parent.cryptor.encrypt_bytes_to_str(
                        serialized_arguments, pub_key
                    ),
                }
            )

        request_payload = {
            "label": label,
            "task": {
                "method": method,
                "image": image,
                "organizations": organization_json_list,
            },
        }

        if name is not None:
            request_payload["name"] = name
        if store is not None:
            request_payload["task"]["store_id"] = store

        df = self.parent.request(
            f"session/{session_id}/dataframe", method="POST", json=request_payload
        )

        if display:
            rich_dataframe_table(df)

        return df

    @post_filtering(iterable=False)
    def preprocess(self, id_: int, image: str, method: str, arguments: dict) -> dict:
        """
        Modify a dataframe in a session.

        Dataframes can be modified by preprocessing them. Preprocessing is handled in
        a sequential manner. In other words, you can add many preprocessing steps to a
        dataframe, and they will be executed one after the other in order of creation.

        The modification will be done after all computation tasks have been executed.
        This is to avoid that a dataframe is modified while it is being used in a
        computation task.

        Parameters
        ----------
        id_: int
            The ID of the dataframe.
        image : str
            The name of the image that will be used to preprocess the dataframe.
        method: str
            Method on the algorithm image to be used to preprocess the dataframe
        arguments: dict
            Arguments for the algorithm method. The dictionary should contain
            the same keys as the arguments of the algorithm method.

        Returns
        -------
        dict
            The dataframe details.
        """

        # Get the organizations that are part of the session.
        dataframe = self.parent.request(f"session/{id_}")
        if not dataframe:
            self.parent.log.error(f"An error occurred while fetching dataframe {id_}")
            return

        if dataframe["study"]:
            params = {"study": dataframe["study"]}
        elif dataframe["collaboration"] and dataframe["collaboration"]["id"]:
            collaboration_id = dataframe["collaboration"]["id"]
            params = {"collaboration": collaboration_id}
        else:
            self.parent.log.error(
                f"No study or collaboration id defined in dataframe {id_}"
            )
            return

        org = self.parent.organization.list(**params)
        organizations = [(o["id"], o["public_key"]) for o in org["data"]]

        # Data will be serialized in JSON.
        serialized_arguments = serialize(arguments)

        # Encrypt the input arguments per organization using that organization's public
        # key.
        organization_json_list = []
        for org_id, pub_key in organizations:
            organization_json_list.append(
                {
                    "id": org_id,
                    "arguments": self.parent.cryptor.encrypt_bytes_to_str(
                        serialized_arguments, pub_key
                    ),
                }
            )

        return self.parent.request(
            f"session/dataframe/{id_}/preprocess",
            method="POST",
            json={
                "dataframe_id": id_,
                "task": {
                    "method": method,
                    "image": image,
                    "organizations": organization_json_list,
                },
            },
        )

    @post_filtering(iterable=False)
    def delete(self, id_: int) -> dict:
        """
        Delete a dataframe.

        Parameters
        ----------
        id_: int
            The ID of the dataframe.
        """

        res = self.parent.request(f"session/dataframe/{id_}", method="DELETE")

        self.parent.log.info(f"--> {res.get('msg')}")
