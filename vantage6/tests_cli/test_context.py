import unittest


class ContextReExportTest(unittest.TestCase):
    """CLI context modules must re-export the same class objects, not copies."""

    def test_node_context_is_the_same_class_object(self):
        from vantage6.cli.context.node import NodeContext as CLINodeContext
        from vantage6.common.node_context import NodeContext as CommonNodeContext

        self.assertIs(CLINodeContext, CommonNodeContext)

    def test_server_context_is_the_same_class_object(self):
        from vantage6.cli.context.server import ServerContext as CLIServerContext
        from vantage6.common.server_context import (
            ServerContext as CommonServerContext,
        )

        self.assertIs(CLIServerContext, CommonServerContext)

    def test_base_server_context_is_the_same_class_object(self):
        from vantage6.cli.context.base_server import (
            BaseServerContext as CLIBaseServerContext,
        )
        from vantage6.common.server_context import (
            BaseServerContext as CommonBaseServerContext,
        )

        self.assertIs(CLIBaseServerContext, CommonBaseServerContext)


if __name__ == "__main__":
    unittest.main()
