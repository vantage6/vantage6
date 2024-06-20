from vantage6.common.client.client_base import ClientBase


class PolicySubClient(ClientBase.SubClient):
    """Subclient for the algorithm store policies."""

    def get(self, public: bool = False) -> dict:
        """
        Get the policies of the algorithm store.

        Parameters
        ----------
        public : bool, optional
            If True, only the public policies are returned. If False, all policies
            are returned.

        Returns
        -------
        list[dict]
            The policies of the algorithm store.
        """
        public_or_not = "/public" if public else ""
        return self.parent.request(
            f"policy{public_or_not}",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )
