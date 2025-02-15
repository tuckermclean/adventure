from __future__ import annotations
import cmd2, os, shlex, sys, yaml
from entities import Room, Door, Item, Entity
from items import Money, Wearable, Useable, Eatable, Computer, Phone
from characters import Character, AICharacter, WalkerCharacter 

class Adventure(cmd2.Cmd):
    def __init__(self, player=None, file="world.yaml"):
        self.prompt = "> "
        self.file = file
        Entity.set_game(self)
        Entity.set_player(player)
        
        # Load the world from a file
        if os.path.exists(self.file):
            with open(self.file, 'r') as stream:
                try:
                    world = yaml.safe_load(stream)
                    for room in world['rooms']:
                        Room(**room)
                        for item in room['items']:
                            # Return the item class based on the item type
                            item_class = globals()[item['type']]
                            if 'func' in item:
                                def closure(func):
                                    return lambda: eval(func)
                                item['func'] = closure(item['func']) or True
                            item_class(**item)
                            Room.get(room['name']).add_item(item_class.get(item['name']))
                    for door in world['doors']:
                        door['room1'] = Room.get(door['room1'])
                        door['room2'] = Room.get(door['room2'])
                        door['key'] = Item.get(door['key'])
                        Door(**door)
                    for character in world['characters']:
                        character_class = globals()[character['type']]
                        character_class(**character)
                        character_class.get(character['name']).go(Room.get(character['current_room']))
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
        print("Items you have:", list(Entity.player.inv_items.keys()), " --  Money: $", '{:.2f}'.format(Entity.player.money))

    def do_where(self, arg=None):
        """Show current room info"""
        self.current_room_intro()

    def do_exit(self, arg=None):
        """Quit the game"""
        quit()

    def do_reset(self, arg=None):
        """Reset the game"""
        self.postloop()
        Entity.world = Entity("world")
        Adventure.game = Adventure()
        Adventure.game.cmdloop()

    def postloop(self):
        return True

    def emptyline(self):
        pass

    def completedefault(self, text, line, begidx, endidx):
        command = shlex.split(line)
        try:
            item = command[1].lower()
        except IndexError:
            item = ""
        action = command[0].lower()
        items = []
        for action_item in Entity.player.current_room.get_actions()[action]:
            items.append(action_item.name)
        return [i for i in items if i.startswith(item)]

    def get_all_commands(self):
        return list(Entity.player.current_room.get_actions().keys()) + ['exit', 'help', 'inv', 'reset', 'where']

    def default(self, line):
        command = shlex.split(line.raw)
        try:
            item = Entity.get(command[1].lower())
            action = command[0].lower()
            if Entity.player.in_room_items(item) or item in Entity.player.inv_items.values():
                if not item.do(action):
                    print("I don't know how to do that")
            else:
                print("I don't know how to do that")
        except:
            print("I don't know how to do that")
        
    def current_room_intro(self):
        for char in dict(filter(lambda pair : Entity.player.in_room_items(pair[1]), Character.get_all().items())).values():
            char.loopit()
        print('You are in:', Entity.player.current_room.name.upper(), ' -- ', Entity.player.current_room.description)
        print('In this room, there are:', list(dict(filter(lambda pair : pair[1] != Entity.player, Entity.player.current_room.get_items().items())).keys()))
        print('The rooms next door:', list(Entity.player.current_room.get_rooms().keys()))
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
    player = Character(lookable=False)
    game = Adventure(player)
    game.cmdloop()
