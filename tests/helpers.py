import string, random
from adventure import *

def randtext(k=5):
    return ''.join(random.choices(string.ascii_letters, k=k))

def wipe_world():
    Entity.world = Entity("world")

def dummy(cls = Entity):
    return cls(randtext(), randtext(k=20))

def dummy_tree(cls = Entity, depth=3, display=False, root=None):
    if root == None:
        root = dummy()
    else:
        root = cls.get(root)
    for i in range(depth):
        for e1 in list(root.traverse(entities={root.name: root})):
            e1 = cls.get(e1)
            e2 = dummy()
            e1.link(e2)
            e2.link(e1)
    if display:
        for e in list(Entity.world.linked.values()):
            print("NAME", e.name, "LINKED", e.linked)
        print("DEPTH", depth, 'NUM OF ENTITIES TOTAL', len(Entity.world.linked))
    return root

def test_world_exists():
    wipe_world()
    assert Entity.world.name == "world"
    assert isinstance(Entity.world, Entity)
    assert len(Entity.world.linked) == 0
