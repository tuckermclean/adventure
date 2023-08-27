import pytest, string, random
from adventure import *

def randtext(k=5):
    return ''.join(random.choices(string.ascii_letters, k=k))

def test_world_exists():
    assert Entity.world.name == "world"
    assert isinstance(Entity.world, Entity)

def wipe_world():
    Entity.world = Entity("world")

def dummy():
    return Entity(randtext(), randtext(k=20))

def dummy_tree(depth=3, display=False, root=None):
    if root == None:
        root = dummy()
    else:
        root = Entity.get(root)
    for i in range(depth):
        for e1 in list(root.traverse(entities={root.name: root})):
            e1 = Entity.get(e1)
            e2 = dummy()
            e1.link(e2)
            e2.link(e1)
    if display:
        for e in list(Entity.world.linked.values()):
            print("NAME", e.name, "LINKED", e.linked)
        print("DEPTH", depth, 'NUM OF ENTITIES TOTAL', len(Entity.world.linked))
    return root
    
def test_link():
    e1 = dummy()
    e2 = dummy()
    e1.link(e2)
    print("E1 LINKED", e1.linked)
    assert e1.linked[e2.name] == e2

def test_get_linked():
    e1 = list(Entity.world.linked.values())[0]
    assert Entity.world.get_linked(e1.name) == e1

def test_pop():
    e2 = list(Entity.world.linked.values())[1]
    e2_popped = Entity.world.pop(e2.name)
    with pytest.raises(KeyError):
        Entity.world.get_linked(e2.name)

@pytest.fixture
def dummy_tree_root(depth):
    wipe_world()
    root = dummy()
    dummy_tree(root=root.name, depth=depth)
    yield root

@pytest.mark.parametrize("depth", [1,2,3,4,5,6,7,8])
def test_build_tree(depth):
    wipe_world()
    root = dummy_tree(depth=depth)
    assert len(Entity.world.linked) == len(root.traverse()) == 2 ** depth

@pytest.mark.parametrize("depth", [3,4,5,6,7,8])
def test_build_tree_with_random_loopback(depth):
    wipe_world()
    root = dummy_tree(depth=depth)
    Entity.root = root
    while True:
        try:
            Entity.random_entity = random.choice(list(Entity.world.linked.values()))
            root.link(Entity.random_entity)
            break
        except EntityLinkException:
            pass
    assert len(Entity.world.linked) == len(root.traverse()) == 2 ** depth

def test_is_linked():
    assert Entity.root.is_linked(Entity.random_entity.name)

def test_is_not_linked():
    while True:
        another_random_entity = random.choice(list(Entity.world.linked.values()))
        if not another_random_entity == Entity.random_entity:
            break
    assert not Entity.root.is_linked(another_random_entity)

def test_get_all():
    assert Entity.get_all() == dict(Entity.world.linked.items())

def test_get():
    assert Entity.get(Entity.root.name) == Entity.root

def test_purge():
    popped = Entity.purge(Entity.random_entity.name)
    assert popped == 1
    assert not Entity.random_entity.name in dict(Entity.world.linked.items())
    assert not Entity.random_entity.name in Entity.root.traverse()