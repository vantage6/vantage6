from vantage6.node.k8s.container_manager import ContainerManager


class TestGetImagePullPolicy:
    def _manager_with_policies(self, policies: dict) -> ContainerManager:
        manager = ContainerManager.__new__(ContainerManager)
        manager._policies = policies
        return manager

    def test_require_algorithm_pull_false_means_if_not_present(self):
        manager = self._manager_with_policies({"require_algorithm_pull": False})
        assert manager._get_image_pull_policy() == "IfNotPresent"

    def test_require_algorithm_pull_true_means_always(self):
        manager = self._manager_with_policies({"require_algorithm_pull": True})
        assert manager._get_image_pull_policy() == "Always"

    def test_require_algorithm_pull_absent_defaults_to_always(self):
        manager = self._manager_with_policies({})
        assert manager._get_image_pull_policy() == "Always"
