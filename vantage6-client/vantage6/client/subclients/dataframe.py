from vantage6.client import ClientBase
from vantage6.client.filter import post_filtering


class DataFrameSubClient(ClientBase.SubClient):
    """Sub client data frames."""

    @post_filtering(iterable=False)
    def get(self, handle: int, session: int = None) -> dict:
        """Get a data frame by its id."""

        session_id = session or self.parent.session_id
        if not session_id:
            self.parent.log.error(
                "No session ID provided and no session ID set in the client."
            )
            return

        return self.parent.request(f"session/{session_id}/dataframe/{handle}")

    @post_filtering()
    def list(self):
        """List all data frames."""
        pass

    @post_filtering(iterable=False)
    def update():
        """Modify a data frame."""
        pass

    @post_filtering(iterable=False)
    def create():
        """Create a new data frame."""
        pass

    @post_filtering(iterable=False)
    def delete():
        """Delete a data frame."""
        pass
