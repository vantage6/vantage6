import logging
import unittest

# from pathlib import Path
# from click.testing import CliRunner
# from prompt_toolkit.input.defaults import create_pipe_input

# from joey.util import NodeContext, TestContext

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from joey.server.models import (
    Base,
    User
)

log = logging.getLogger(__name__.split(".")[-1])
log.level = logging.DEBUG

class TestQuery(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.session = Session(self.engine)
        Base.metadata.create_all(self.engine)
        # self.panel = Panel(1, 'ion torrent', 'start')
        # self.session.add(self.panel)
        self.session.commit()
    
    def trearDown(self):
        Base.metadata.drop_all(self.engine)

    def test_files_using_name(self):
        assert 1 == 1