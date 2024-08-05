import pandas as pd

from rich.table import Table
from rich.console import Console

from vantage6.common.serialization import serialize
from vantage6.client import ClientBase
from vantage6.client.filter import post_filtering
from vantage6.client.rich.table import rich_dataframe_table, rich_dataframe_schema_table


class DataFrameSubClient(ClientBase.SubClient):
    """Sub client data frames."""

    @post_filtering(iterable=False)
    def get(self, handle: int, session: int = None, display=False) -> dict:
        """Get a data frame by its id."""

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
    def list(self, session: int = None, display=False):
        """List all data frames."""
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
    def create(self, database, image, input_, session: int = None, display=False):
        """Create a new data frame."""

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
    def preprocess(self, handle, database, image, input_, session: int = None):
        """Create a new data frame."""

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
            f"session/{session_id}/dataframe/{handle}",
            method="POST",
            json={
                "task": {
                    "image": image,
                    "organizations": organization_json_list,
                },
            },
        )

    @post_filtering(iterable=False)
    def delete():
        """Delete a data frame."""
        pass
