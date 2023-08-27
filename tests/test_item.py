import pytest, string, random
from adventure import *
from helpers import *

def test_items():
    item1 = dummy(Item)
    item2 = dummy(Item)
    item3 = dummy(Item)
    item2.add_item(item3)

    assert len(Item.get_all()) == 3
    assert item3.name in item2.linked.keys()

def test_item_add_action():
    wipe_world()
    item = dummy(Item)
    item.add_action("doink1", lambda: "doink2")
    assert item.actions["doink1"]() == "doink2"

def test_item_do():
    item = list(Entity.get_all().values())[0]
    assert item.do("doink1") == "doink2"

def test_item_get_all():
    wipe_world()
    for i in range(3):
        dummy(Entity)
        dummy(Item)
        dummy(Room)
    assert len(Item.get_all()) == 3

def test_item_get():
    item = list(Item.get_all().values())[0]
    assert Item.get(item.name) == item

def test_money():
    for i in range(3):
        dummy(Money).amount = random.random()*random.random()
    assert len(Money.get_all()) == 3
    assert len(Item.get_all()) == 6
    assert len(Room.get_all()) == 3
    assert len(Entity.get_all()) == 12

def test_rooms():
    wipe_world()
    for i in range(5):
        item1 = dummy(Item)
        item2 = dummy(Item)
        room = dummy(Room)
        room.add_item(item1)
        room.add_item(item2)
        randtext1 = randtext()
        randtext2 = randtext()
        item1.add_action(randtext1, lambda: f"{item1.name}+{randtext1}")
        item1.add_action(randtext2, lambda: f"{item1.name}+{randtext2}")
        item2.add_action(randtext1, lambda: f"{item2.name}+{randtext1}")
        item2.add_action(randtext2, lambda: f"{item2.name}+{randtext2}")
    rooms = list(Room.get_all().values())
    rooms[0].link_room(rooms[1])
    rooms[1].link_room(rooms[2])
    rooms[2].link_room(rooms[3])
    rooms[3].link_room(rooms[4])
    rooms[4].link_room(rooms[0])
    another_room = dummy(Room)
    door = Door(randtext(), rooms[0], another_room)
    Entity.another_room = another_room
    Entity.first_room = rooms[0]
    Entity.door = door
    assert len(Room.get_all()) == 7
    assert rooms[1].name in rooms[0].get_rooms()
    assert rooms[4].name in rooms[0].get_rooms()
    assert rooms[0].name in rooms[1].get_rooms()
    assert rooms[0].name in rooms[4].get_rooms()

def test_room_actions():
    rooms = list(Room.get_all().values())
    assert len(rooms[0].get_actions()) == 2
    assert not rooms[0].get_actions() == rooms[1].get_actions()

def test_room_get_rooms():
    assert len(Entity.first_room.get_rooms()) == 3

def test_room_get_doors():
    assert len(Entity.first_room.get_doors()) == 1

def test_door():
    wipe_world()
    Entity.room1 = dummy(Room)
    Entity.room2 = dummy(Room)
    Entity.key = dummy(Item)
    Entity.item = dummy(Item)
    Entity.door = Door(randtext(), Entity.room1, Entity.room2, key=Entity.key)
    assert Entity.door.locked == True

def test_door_other():
    assert Entity.door.get_other(Entity.room1) == Entity.room2
    assert Entity.door.get_other(Entity.room2) == Entity.room1

def test_door_unlock():
    assert Entity.door.unlock(Entity.item) == False
    assert Entity.door.locked == True
    assert Entity.door.unlock(Entity.key) == True
    assert Entity.door.locked == False

def test_door_lock():
    assert Entity.door.lock(Entity.item) == False
    assert Entity.door.locked == False
    assert Entity.door.lock(Entity.key) == True
    assert Entity.door.locked == True