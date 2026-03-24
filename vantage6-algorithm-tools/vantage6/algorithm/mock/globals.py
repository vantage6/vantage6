from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class MockDatabase:
    label: str
    database: pd.DataFrame | Path
    db_type: str | None
