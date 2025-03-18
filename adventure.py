from __future__ import annotations
import cmd2, os, shlex, sys, yaml
from entities import Room, Door, HiddenDoor, Item, Entity
from items import Money, Wearable, Useable, Eatable, Computer, Phone, Weapon
from characters import Character, AICharacter, WalkerCharacter, NonPlayerCharacter
from news import News

class Adventure(cmd2.Cmd):
    def __init__(self, player=None, file="world.yaml"):
        self.prompt = "> "
        if len(sys.argv) > 1:
            self.file = sys.argv[1]
        else:
            self.file = file
        Entity.set_game(self)
        Entity.set_player(player)
        
        # Load the world from a file
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding="utf-8") as stream:
                try:
                    world = yaml.safe_load(stream)
                    for room in world['rooms']:
                        Room(**room)
                        for item in room['items']:
                            # Return the item class based on the item type
                            item_class = globals()[item['type']]
                            if 'func' in item:
                                def closure(func):
                                    return lambda var=None: exec(func)
                                item['func'] = closure(item['func']) or True
                            item_class(**item)
                            Room.get(room['name']).add_item(item_class.get(item['name']))
                    for door in world['doors']:
                        door['room1'] = Room.get(door['room1'])
                        door['room2'] = Room.get(door['room2'])
                        try:
                            door['key'] = Item.get(door['key'])
                        except:
                            pass
                        if door.get('hidden', False):
                            if 'condition' in door:
                                def closure(condition):
                                    return lambda var=None: eval(condition)
                                door['condition'] = closure(door['condition']) or True
                            HiddenDoor(**door)
                        else:
                            Door(**door)
                    for character in world['characters']:
                        character_class = globals()[character['type']]
                        if 'func' in character:
                            def closure(func):
                                return lambda var=None: exec(func)
                            character['func'] = closure(character['func']) or True
                        character_obj = character_class(**character)
                        character_obj.go(Room.get(character['current_room']))
                        try:
                            if character_class == AICharacter and character['news'] == True:
                                News.subscribe(character_obj)
                        except:
                            pass
                    for help in world['help']:
                        text = world['help'][help]
                        setattr(self, f"help_{help}", lambda text=text: print(text))
                except yaml.YAMLError as exc:
                    print(exc)
            # Go to first room
            Entity.player.go(list(Room.get_all().values())[0])
        else:
            print("No world file found.")

        super().__init__()

    def do_inv(self, arg=None):
        """List items in inventory"""

    def do_exit(self, arg=None):
        """Quit the game"""
        quit()

    def do_reset(self, arg=None):
        """Reset the game"""
        self.postloop()
        Entity.world = Entity("world")
        Entity.player = Character(lookable=False)
        Entity.game = Adventure(Entity.player)
        Entity.game.cmdloop()

    def postloop(self):
        return True

    def emptyline(self):
        pass

    def completedefault(self, text, line, begidx, endidx):
        """
        Provide custom tab-completion for adventure actions.
        - Gracefully handles invalid commands or quotes.
        - Returns partial matches for item names.
        """

        # Attempt to parse the line safely. If there's a mismatch in quotes,
        # shlex.split() might raise a ValueError, so we fall back to a simpler approach.
        try:
            tokens = shlex.split(line, posix=False)
        except ValueError:
            # Simple fallback if there are unbalanced quotes
            # e.g. user typed: take "some item
            tokens = line.strip().split()

        if not tokens:
            return []  # No tokens at all, no completions

        # First token is the action, e.g. 'take', 'look', 'go'
        action = tokens[0].lower()

        # Attempt to isolate the partial item text
        # If there's more than one token, treat the second as the item
        if len(tokens) > 1:
            # Strip leading/trailing quotes
            item_partial = " ".join(tokens[1:]).strip('"').strip("'").lower()
        else:
            item_partial = ""

        # Get all possible actions from the current room
        actions_dict = Entity.player.current_room.get_actions()
        # e.g. { 'take': [<Item1>, <Item2>], 'look': [...], 'go': [...], ... }

        # If the action doesn't exist, return empty
        if action not in actions_dict:
            return []

        # Gather possible item names for this action
        possible_items = [
            entity_item.name for entity_item in actions_dict[action]
            if not isinstance(entity_item, HiddenDoor)
            or (isinstance(entity_item, HiddenDoor) and entity_item.condition())
        ]

        # Filter:
        # 1) Must start with item_partial
        # 2) Must NOT exactly equal item_partial (skip if already fully typed)
        completions = [
            item_name for item_name in possible_items
            if item_name.lower().startswith(item_partial)
            and item_name.lower() != item_partial
        ]

        # If user typed something like:
        #   take "sho
        # then text == '"sho' (starts with a quote but not ended).
        # We'll auto-add a trailing quote to each completion for a nicer experience.
        if text.startswith('"') and not text.endswith('"'):
            # Make sure the user sees a final quote
            completions = [c + '"' for c in completions]

        return completions

    def get_all_commands(self):
        return list(Entity.player.current_room.get_actions().keys()) + ['exit', 'help', 'reset']

    def default(self, line):
        command = shlex.split(line.raw)
        action = command[0].lower()
        try:
            if command[0].lower() == "look" and len(command) == 1:
                self.current_room_intro()
                return
            try:
                item_name = " ".join(command[1:]).lower().strip()
            except Exception as e:
                print(e)
                item_name = None
            if not item_name:
                return
            item = Entity.get(item_name)
            if Entity.player.in_room_items(item) or item in Entity.player.inv_items.values():
                try:
                    if not item.do(action):
                        print(f"I don't know how to do '{action}' to '{item_name}'")
                except Exception as e:
                    print(f"I couldn't do '{action}' to '{item_name}': {type(e)}")
            else:
                print(f"I don't see that item here: {item_name}")
        except Exception as e:
            print(f"I couldn't do '{action}' to '{item_name}': {type(e)}")
        
    def current_room_intro(self):
        for char in dict(filter(lambda pair : Entity.player.in_room_items(pair[1]), Character.get_all().items())).values():
            char.loopit()
        print('You are in:', Entity.player.current_room.name.upper(), ' -- ', Entity.player.current_room.description)
        print('In this room, there are:', list(dict(filter(lambda pair : pair[1] != Entity.player, Entity.player.current_room.get_items().items())).keys()))
        print('The rooms next door:', list(Entity.player.current_room.get_rooms().keys()))
        print("Items you have:", list(Entity.player.inv_items.keys()), " --  Money: $", '{:.2f}'.format(Entity.player.money))
        print()
        for char in dict(filter(lambda pair : Entity.player.in_room_items(pair[1]) and pair[1] != Entity.player, Character.get_all().items())).values():
            try:
                if char.words != "":
                    print(f"{char.description}\t{char.words}")
                else:
                    print(f"{char.description}")
            except:
                print(f"{char.description}")
                
    def preloop(self):
        print("Welcome to the adventure game!   Type help or ? to list commands.\n")
        self.current_room_intro()

if __name__ == '__main__':
    player = Character(lookable=False, health=3)
    game = Adventure(player)
    game.cmdloop()
