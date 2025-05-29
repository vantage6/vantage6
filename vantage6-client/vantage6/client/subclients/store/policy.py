from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class PolicySubClient(ClientBase.SubClient):
    """Subclient for the algorithm store policies."""

    @post_filtering(iterable=False)
    def get(self, public: bool = False) -> dict:
        """
        Get the policies of the algorithm store.

        Parameters
        ----------
        public : bool, optional
            If True, only the public policies are returned. If False, all policies
            are returned.
        field: str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the policy. Default is None.
        fields: list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            policy. Default is None.

        Returns
        -------
        list[dict]
            The policies of the algorithm store.
        """
        public_or_not = "/public" if public else ""
        return self.parent.request(
            f"policy{public_or_not}",
            is_for_algorithm_store=True,
        )
