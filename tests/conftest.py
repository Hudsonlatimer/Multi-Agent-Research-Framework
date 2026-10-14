import re

import pytest


def pytest_collection_modifyitems(config, items):
    markexpr = config.getoption("markexpr") or ""
    wants_live = bool(re.search(r"(^|\s)live(\s|$)", markexpr)) and "not live" not in markexpr
    if wants_live:
        return
    skip_live = pytest.mark.skip(reason="live test; run pytest -m live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
