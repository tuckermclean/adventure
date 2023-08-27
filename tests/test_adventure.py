import pytest
from adventure import *

@pytest.fixture
def setup_world():
    adventure = Adventure()
    yield

def test_world_exists(setup_world):
    assert Entity.world.name == "world" and isinstance(Entity.world, Entity)

