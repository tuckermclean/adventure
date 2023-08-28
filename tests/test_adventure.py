import pytest, random
from adventure import *
from helpers import *

def test_make_world():
    Adventure.game = Adventure()
    assert Adventure.game.player.current_room == Room.get("living room")

def test_in_rooms():
    assert Adventure.game.player.in_rooms(Room.get(random.choice(list(Adventure.game.player.current_room.get_rooms().keys()))))

def test_in_room_items():
    assert Adventure.game.player.in_room_items(Item.get(random.choice(list(Adventure.game.player.current_room.get_items().keys()))))

def test_do_go():
    assert Adventure.game.player.in_room_items(Adventure.game.player)
    old_room = Adventure.game.player.current_room
    new_room = random.choice(list(Adventure.game.player.current_room.get_rooms().keys()))
    Adventure.game.do_go(new_room)
    assert Adventure.game.player.current_room == Room.get(new_room)
    assert Adventure.game.player.in_room_items(Adventure.game.player)
    assert not Adventure.game.player in list(old_room.get_items().keys())

def test_do_unlock():
    door = Door.get(random.choice(list(Door.get_all().keys())))
    Adventure.game.player.current_room = random.choice(list(door.get_rooms().values()))
    Adventure.game.do_unlock(door.name)
    assert door.locked
    Adventure.game.player.inv_items[door.key.name] = door.key
    Adventure.game.do_unlock(door.name)
    assert not door.locked
    Adventure.game.player.inv_items = {}

#@pytest.mark.parametrize("num_to_take",range(len(dict(filter(lambda pair : pair[1].takeable, Item.get_all().values())))))
@pytest.mark.parametrize("num_to_take",[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])
def test_do_take(num_to_take):
    for room in Room.get_all().values():
        for item in list(room.get_items().keys()):
            item_ent = Item.get(item)
            if not item_ent.droppable == False:
                Adventure.game.player.current_room = room
                Adventure.game.do_take(item)
                if (not item_ent.__class__ == Money):
                    if num_to_take > Adventure.game.player.max_items:
                        assert not len(Adventure.game.player.inv_items) > Adventure.game.player.max_items
                    else:
                        assert Adventure.game.player.inv_items[item] == item_ent
            if len(Adventure.game.player.inv_items) >= num_to_take:
                break
        if len(Adventure.game.player.inv_items) >= num_to_take:
            break
    if num_to_take > Adventure.game.player.max_items:
        assert not len(Adventure.game.player.inv_items) > Adventure.game.player.max_items
    else:
        assert len(Adventure.game.player.inv_items) == num_to_take
    
    while len(Adventure.game.player.inv_items) > 0:
        for room in Room.get_all().values():
            Adventure.game.player.current_room = room
            first_len = len(Adventure.game.player.inv_items)
            item = random.choice(list(Adventure.game.player.inv_items.keys()))
            Adventure.game.do_drop(item)
            now_len = len(Adventure.game.player.inv_items)
            assert now_len == first_len - 1
            print("ITEM", item)
            if len(Adventure.game.player.inv_items) == 0:
                break

    assert len(Adventure.game.player.inv_items) == 0

def test_do_drop():
    for item in list(filter(lambda item : item.takeable and item.droppable and not item.__class__ == Money, Item.get_all().values())):
        for room in list(filter(lambda room : item in room.get_items().values(), Room.get_all().values())):
            Adventure.game.player.current_room = room
            Adventure.game.do_take(item.name)
            assert len(Adventure.game.player.inv_items) == 1
            Adventure.game.do_drop(item.name)
            assert len(Adventure.game.player.inv_items) == 0
            Adventure.game.do_take(item.name)
            assert len(Adventure.game.player.inv_items) == 1
            item.droppable = False
            Adventure.game.do_drop(item.name)
            assert len(Adventure.game.player.inv_items) == 1
            item.droppable = True
            Adventure.game.do_drop(item.name)
            assert len(Adventure.game.player.inv_items) == 0