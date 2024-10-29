from vantage6.common.serialization import serialize
from vantage6.client import ClientBase
from vantage6.client.filter import post_filtering
from vantage6.client.rich.table import rich_dataframe_table, rich_dataframe_schema_table


class DataFrameSubClient(ClientBase.SubClient):
    """Sub client data frames."""

    @post_filtering(iterable=False)
    def get(self, handle: str = None, session: int = None, display=False) -> dict:
        """
        Get a data frame by its ID or by supplying the handle and session ID.

        Parameters
        ----------
        handle : str
            The name of the data frame
        session : int, optional
            The session ID in which the data frame is located. When not provided, the
            session ID of the client is used when it is set. In case the session ID is
            not set, an error is printed.
        display : bool, optional
            Whether to print the data frame details. By default False.

        Returns
        -------
        dict
            The data frame details.
        """
        session_id = session or self.parent.session_id
        if not session_id:
            self.parent.log.error(
                "No session ID provided and no session ID set in the client."
            )
            return

        df = self.parent.request(f"session/{session_id}/dataframe/{handle}")
        if display:
            rich_dataframe_table(df)
            rich_dataframe_schema_table(df)

        return df

    @post_filtering()
    def list(self, session: int = None, display=False) -> dict:
        """
        List all data frames.

        Parameters
        ----------
        session : int, optional
            The session ID in which the data frame is located. When not provided, the
            session ID of the client is used when it is set. In case the session ID is
            not set, an error is printed.
        display : bool, optional
            Whether to print the list of data frame details. By default False.

        Returns
        -------
        dict
            List of data frame details.
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
        database: str,
        image: str,
        input_: dict,
        session: int = None,
        display=False,
    ) -> dict:
        """
        Create a new data frame in a session.

        Parameters
        ----------
        database : str
            The name of the database. This is the label of the source database at the
            node.
        image : str
            The name of the image that will be used to retrieve the data from the
            source database.
        input_: dict
            The input for the data frame creation.
        session : int, optional
            The session ID in which the data frame is located. When not provided, the
            session ID of the client is used when it is set. In case the session ID is
            not set, an error is printed.
        display : bool, optional
            Whether to print the data frame details. By default False.

        Returns
        -------
        dict
            The data frame details.
        """

        session_id = session or self.parent.session_id
        if not session_id:
            self.parent.log.error(
                "No session ID provided and no session ID set in the client."
            )
            return

        # Get the organizations that are part of the session.
        session = self.parent.request(f"session/{session_id}")
        if session.get("study"):
            study_id = session["study"]["id"]
            params = {"study": study_id}
        else:
            collaboration_id = session["collaboration"]["id"]
            params = {"collaboration": collaboration_id}

        orgs = self.parent.organization.list(**params)
        organizations = [(o["id"], o["public_key"]) for o in orgs["data"]]

        # Data will be serialized in JSON.
        serialized_input = serialize(input_)

        # Encrypt the input per organization using that organization's
        # public key.
        organization_json_list = []
        for org_id, pub_key in organizations:
            organization_json_list.append(
                {
                    "id": org_id,
                    "input": self.parent.cryptor.encrypt_bytes_to_str(
                        serialized_input, pub_key
                    ),
                }
            )

        df = self.parent.request(
            f"session/{session_id}/dataframe",
            method="POST",
            json={
                "label": database,
                "task": {
                    "image": image,
                    "organizations": organization_json_list,
                },
            },
        )

        if display:
            rich_dataframe_table(df)

        return df

    @post_filtering(iterable=False)
    def preprocess(
        self, handle: str, image: str, input_: dict, session: int = None
    ) -> dict:
        """
        Modify a data frame in a session.

        Data frames can be modified by preprocessing them. Preprocessing is handles in
        a sequential manner. In other words, you can add many preprocessing steps to a
        data frame, they will be executed one after the other.

        The modification will be done after all computation tasks have been executed.
        This is to avoid that a data frame is modified while it is being used in a
        computation task.

        Parameters
        ----------
        handle : str
            The name of the data frame.
        image : str
            The name of the image that will be used to preprocess the data frame.
        input_: dict
            The input for the data frame preprocessing.
        session : int, optional
            The session ID in which the data frame is located. When not provided, the
            session ID of the client is used when it is set. In case the session ID is
            not set, an error is printed.

        Returns
        -------
        dict
            The data frame details.
        """

        session_id = session or self.parent.session_id
        if not session_id:
            self.parent.log.error(
                "No session ID provided and no session ID set in the client."
            )
            return

        # Get the organizations that are part of the session.
        session = self.parent.request(f"session/{session_id}")
        if session.get("study"):
            study_id = session["study"]["id"]
            params = {"study": study_id}
        else:
            collaboration_id = session["collaboration"]["id"]
            params = {"collaboration": collaboration_id}

        org = self.parent.organization.list(**params)
        organizations = [(o["id"], o["public_key"]) for o in org["data"]]

        # Data will be serialized in JSON.
        serialized_input = serialize(input_)

        # Encrypt the input per organization using that organization's public key.
        organization_json_list = []
        for org_id, pub_key in organizations:
            organization_json_list.append(
                {
                    "id": org_id,
                    "input": self.parent.cryptor.encrypt_bytes_to_str(
                        serialized_input, pub_key
                    ),
                }
            )

        return self.parent.request(
            f"session/{session_id}/dataframe/{handle}/preprocess",
            method="POST",
            json={
                "task": {
                    "image": image,
                    "organizations": organization_json_list,
                },
            },
        )

    @post_filtering(iterable=False)
    def delete(self):
        """Delete a data frame."""
        # TODO: https://github.com/vantage6/vantage6/issues/1476
        self.parent.log.error("Not implemented yet.")
