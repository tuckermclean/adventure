import pytest
import random
from adventure import *
from helpers import *

def test_make_world():
    """
    Simply instantiate the game and make sure the player is in the living room.
    """
    Adventure.player = Character(lookable=False)
    Adventure.game = Adventure(Adventure.player)
    assert Adventure.game.player.current_room == Room.get("living room")

def test_in_rooms():
    """
    Check that a random adjacent room is recognized as "in_rooms".
    """
    assert Adventure.game.player.in_rooms(
        Room.get(random.choice(list(Adventure.game.player.current_room.get_rooms().keys())))
    )

def test_in_room_items():
    """
    Check that a random item in the current room is recognized by in_room_items.
    """
    assert Adventure.game.player.in_room_items(
        Item.get(random.choice(list(Adventure.game.player.current_room.get_items().keys())))
    )

def test_do_go():
    """
    Instead of Adventure.game.do_go, call player.go(room) directly.
    This ensures we are testing the actual movement logic, not cmd2.
    """
    player = Adventure.game.player
    old_room = player.current_room
    assert player in old_room.get_items().values()  # player item is in old_room

    # pick a random connected room
    new_room_name = random.choice(list(old_room.get_rooms().keys()))
    new_room = Room.get(new_room_name)

    # move player (ignore adjacency check by passing check_link=False, or rely on it if you want)
    player.go(new_room, check_link=False)

    # Make sure we're in the new room
    assert player.current_room == new_room
    assert player in new_room.get_items().values()
    # Make sure we got popped out of the old room
    assert player not in old_room.get_items().values()

def test_do_unlock():
    """
    Instead of Adventure.game.do_unlock(door.name), call door.unlock() directly.
    """
    # pick a random Door object
    door = Door.get(random.choice(list(Door.get_all().keys())))
    player = Adventure.game.player

    # Move the player into one of the rooms connected by this door
    # (check_link=False so we don't care if it's truly adjacent)
    player.go(random.choice(list(door.get_rooms().values())), check_link=False)

    # First unlock attempt with no key should fail
    door.unlock()
    assert door.locked

    # Give the player the door's key
    player.inv_items[door.key.name] = door.key

    # Now unlocking should succeed
    door.unlock()
    assert not door.locked

    # Clean up key from inventory
    del player.inv_items[door.key.name]
    assert door.key.name not in player.inv_items

def test_do_lock():
    """
    Instead of Adventure.game.do_lock(door.name), call door.lock() directly.
    """
    # pick a random Door object
    door = Door.get(random.choice(list(Door.get_all().keys())))
    player = Adventure.game.player

    # Move the player into one of the rooms connected by this door
    # (check_link=False so we don't care if it's truly adjacent)
    player.go(random.choice(list(door.get_rooms().values())), check_link=False)

    # Give the player the door's key
    player.inv_items[door.key.name] = door.key

    # First unlock the door
    door.unlock()
    assert not door.locked

    # Now lock it
    door.lock()
    assert door.locked

@pytest.mark.parametrize("num_to_take", [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])
def test_do_take(num_to_take):
    """
    Instead of Adventure.game.do_take(itemName), directly call item.do("take").
    We check that the player cannot exceed max_items in inventory, etc.
    """
    player = Adventure.game.player
    player.inv_items = {}  # clear inventory
    # Attempt to pick up items from every room until we've tried num_to_take
    count_taken = 0
    for room in Room.get_all().values():
        # Move the player to this room
        player.go(room, check_link=False)

        for item_name in list(room.get_items().keys()):
            item_ent = Item.get(item_name)
            if not (item_ent.droppable is False):
                # Attempt to "take" by calling the "take" action directly
                item_ent.do("take")

                # If it's not money, the item either goes to inventory
                # or fails if inventory is at max capacity
                if not isinstance(item_ent, Money):
                    if count_taken >= player.max_items:
                        # Ensure we didn't exceed max
                        assert len(player.inv_items) <= player.max_items
                    else:
                        # Either we took it successfully
                        if len(player.inv_items) > count_taken:
                            count_taken += 1
                            # item should be in inventory
                            assert item_name in player.inv_items
                            assert player.inv_items[item_name] == item_ent
                else:
                    # Money is handled differently, it goes into .money
                    assert player.money == item_ent.amount

                # If we've taken 'num_to_take' items, break out
                if len(player.inv_items) >= num_to_take:
                    break
        if len(player.inv_items) >= num_to_take:
            break

    print(player.inv_items)

    # If we wanted to take more than max_items, ensure we didn't exceed it
    if num_to_take > player.max_items:
        assert len(player.inv_items) <= player.max_items
    else:
        assert len(player.inv_items) == num_to_take

    #
    # Now test dropping them all
    #
    while len(player.inv_items) > 0:
        # move to some random room so that we can do drops
        room = random.choice(list(Room.get_all().values()))
        player.go(room, check_link=False)

        first_len = len(player.inv_items)
        # pick a random item from player's inventory
        item_name = random.choice(list(player.inv_items.keys()))
        item_ent = player.inv_items[item_name]

        # drop it
        item_ent.do("drop")

        now_len = len(player.inv_items)
        assert now_len == first_len - 1

def test_do_drop():
    """
    Instead of Adventure.game.do_drop(itemName), call item.do("drop") directly
    to test the drop logic.
    """
    player = Adventure.game.player

    # For every item that is takeable and droppable (and not Money),
    # pick it up, drop it, etc.
    for item in list(
        filter(lambda i: i.takeable and i.droppable and not isinstance(i, Money),
               Item.get_all().values())
    ):
        # Find a room that actually has this item
        for room in filter(lambda r: item in r.get_items().values(), Room.get_all().values()):
            # move player to that room
            player.go(room, check_link=False)

            # Take the item
            item.do("take")
            assert len(player.inv_items) == 1
            assert item.name in player.inv_items

            # Drop it
            item.do("drop")
            assert len(player.inv_items) == 0

            # Take it again
            item.do("take")
            assert len(player.inv_items) == 1

            # Make item temporarily non-droppable
            item.droppable = False
            print(f"Testing item {item.name} droppable={item.droppable}")
            item.do("drop")
            # still have it
            assert len(player.inv_items) == 1

            # Re-enable droppable
            item.droppable = True
            item.do("drop")
            assert len(player.inv_items) == 0

            # once we've tested with this room, continue
            break

def test_do_money_take():
    # Find a room that actually has money
    for room in filter(lambda r: any(isinstance(i, Money) for i in r.get_items().values()), Room.get_all().values()):
        player = Adventure.game.player
        player.inv_items = {}  # clear inventory
        # move player to that room
        player.go(room, check_link=False)

        # Take the money
        player.money = 0
        room_money = list(filter(lambda i: isinstance(i, Money), room.get_items().values()))[0]
        room_money.do("take")
        assert player.money == room_money.amount

def test_do_wear_remove():
    # Find a room with a wearable item
    for room in filter(lambda r: any(isinstance(i, Wearable) for i in r.get_items().values()), Room.get_all().values()):
        player = Adventure.game.player
        player.inv_items = {}  # clear inventory
        # move player to that room
        player.go(room, check_link=False)

        # Take the wearable item
        wearable = list(filter(lambda i: isinstance(i, Wearable), room.get_items().values()))[0]
        wearable.do("take")
        assert wearable.name in player.inv_items

        # Wear it
        wearable.do("wear")
        assert wearable.name in player.wearing

        # Remove it
        wearable.do("remove")
        assert wearable.name not in player.wearing

def test_do_eat():
    # Find a room with an edible item
    for room in filter(lambda r: any(isinstance(i, Eatable) for i in r.get_items().values()), Room.get_all().values()):
        player = Adventure.game.player
        player.inv_items = {}  # clear inventory
        # move player to that room
        player.go(room, check_link=False)

        # Take the edible item
        edible = list(filter(lambda i: isinstance(i, Eatable), room.get_items().values()))[0]
        edible.do("take")
        assert edible.name not in room.get_items().keys()
        assert edible.name in player.inv_items.keys()

        # Eat it
        edible.do("eat")
        assert edible.name not in room.get_items().keys()
        print(player.inv_items)
        assert edible.name not in player.inv_items.keys()

        # Put it back in the room
        room.add_item(edible)
        assert edible.name in room.get_items().keys()

        # Eat it again
        edible.do("eat")
        assert edible.name not in room.get_items().keys()
        assert edible.name not in player.inv_items.keys()