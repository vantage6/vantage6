from vantage6.common.client.client_base import ClientBase
from vantage6.common.enum import StorePolicies, DefaultStorePolicies


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
        response = self.parent.request(
            f"policy{public_or_not}",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )
        # reshape the policies to a more readable format
        # e.g. from
        #   {'value': 'public', 'key': 'algorithm_view'},
        #   {'value': 'http://localhost:5000/api', 'key': 'allowed_servers_edit'},
        #   {'value': 'http://localhost:5005/api', 'key': 'allowed_servers_edit'},
        #   {'value': '1', 'key': 'allow_localhost'}
        # to
        #   {'algorithm_view': 'public',
        #    'allowed_servers_edit': [
        #      'http://localhost:5000/api', 'http://localhost:5005/api'
        #     ],
        #    'allow_localhost': 1}
        policies = {}
        for new_policy in response["data"]:
            policy_name = new_policy["key"]
            if policy_name in policies:
                if isinstance(policies[policy_name], list):
                    policies[policy_name].append(new_policy["value"])
                else:
                    policies[policy_name] = [policies[policy_name], new_policy["value"]]
            else:
                policies[policy_name] = new_policy["value"]

        # add default values for policies that are not in the response
        for policy in [p.value for p in StorePolicies]:
            if policy not in policies:
                policies[policy] = DefaultStorePolicies[policy.upper()].value

        return policies
