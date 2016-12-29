import yaml
from catools.soap import login
import pytest

@pytest.fixture
def cl():
    with open('..\\test_config.yaml') as f:
        params = yaml.load(f)
    return login(**params)

def test_searchObjects(cl):
    assert type(cl.searchObjects('cr', "id is not null", -1, ["ref_num"])[0])==dict()

    # assert cl.searchObjects('cr', "id is COMPLETELY INVALID INPUT", -1, ["ref_num"])[0] == {}

def test_updateObject():
    assert 1

