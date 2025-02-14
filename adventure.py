from __future__ import annotations
import cmd2, code, os, random, re, shlex, sys, yaml
from openai import OpenAI

class EntityLinkException(Exception):
    "Thrown when there is already an Entity with this name"

class NoEntityLinkException(Exception):
    "Thrown when there is no near-enough link to an Entity with this name"

class Entity:
    world = None

    def __init__(self, name = 'No name', description = 'No description'):
        self.name = name
        self.description = description
        self.linked = {}
        self.actions = {}

        if Entity.world != None:
            Entity.world.link(self)

    def __str__(self):
        return f"<{self.__class__}:{self.name}>"

    def __repr__(self):
        return self.__str__()

    def link(self, linked: Entity, override = False):
        if linked.name not in self.linked.keys() or override == True:
            self.linked.update({ f"{linked.name}": linked })
        else:
            raise EntityLinkException

    def get_linked(self, name):
        return self.linked[name]

    def pop(self, name):
        if name in self.linked.keys():
            popped = self.linked[name]
            del self.linked[name]
            return popped
        else:
            raise NoEntityLinkException

    def add_action(self, name="doink", function = lambda: True):
        self.actions[name] = function

    def remove_action(self, name="doink"):
        del self.actions[name]

    def do(self, action):
        try:
            return self.actions[action]()
        except KeyError:
            return None

    def traverse(self, max_levels=-1, first_level=0, entities=None):
        if entities == None:
            entities = {}
        for name in self.linked:
            level = first_level
            if (level < max_levels or max_levels < 0):
                if name not in entities.keys():
                    entities[name] = self.linked[name]                    
                    level = level + 1
                    if (level < max_levels or max_levels < 0):
                        children = self.linked[name].traverse(max_levels, level, entities)
                        for child in children:
                            for key in children.keys():
                                if not key in entities.keys():
                                    entities[name] = child
        return entities

    def is_linked(self, name):
        if name in self.linked:
            return True
        else:
            return False

    @classmethod
    def get_all(cls):
        return dict(filter(lambda pair : isinstance(pair[1], cls) or issubclass(pair[1].__class__, cls), Entity.world.linked.items()))

    @classmethod
    def get(cls, name):
        try:
            return cls.get_all()[name]
        except KeyError:
            raise NoEntityLinkException

    @staticmethod
    def purge(name):
        popped = 0
        for entity in Entity.world.traverse():
            try:
                Entity.get(entity).pop(name)
                popped = popped + 1
            except NoEntityLinkException:
                pass
        try:
            Entity.world.pop(name)
            popped = popped + 1
        except NoEntityLinkException:
            pass

        return popped > 0

Entity.world = Entity("world", "The world as we know it")

class Item(Entity):
    def __init__(self, name = 'item', description = "No description", droppable=True, takeable=True, lookable=True, **kwargs):
        Entity.__init__(self, name, description)
        self.droppable = droppable
        self.takeable = takeable
        if takeable:
            self.add_action("take", self.take)
        if lookable:
            self.add_action("look", self.look)

    def add_item(self, item: Item):
        super().link(item)

    def look(self):
        print(self.name.upper(), " -- " , self.description)
        return True

    def take(self):
        """Take an item"""
        if Adventure.player.in_room_items(self):
            if len(Adventure.player.inv_items) >= Adventure.player.max_items:
                print(f"You already have {Adventure.player.max_items} items, buddy")
            else:
                Adventure.player.inv_items[self.name] = Adventure.player.current_room.pop(self.name)
                self.remove_action("take")
                if self.droppable:
                    self.add_action("drop", self.drop)
                Adventure.game.do_inv()
        else:
            print("That item is not in this room!")
        return True
    
    def drop(self):
        """Drop an item from inventory"""
        if self in Adventure.player.inv_items.values():
            if self.droppable:
                del Adventure.player.inv_items[self.name]
                Adventure.player.current_room.add_item(self)
                self.remove_action("drop")
                if self.takeable:
                    self.add_action("take", self.take)
                Adventure.game.do_inv()
            else:
                print("That item is not droppable, guess you're stuck with it.")
        else:
            print("You don't have that item, dingus")
        return True

#class VendingMachine(Item):
#class Phone(Item):

class Money(Item):
    def __init__(self, name="money", description="some money", amount=1.00, **kwargs):
        super().__init__(name, description, droppable=False)
        self.amount = amount
        self.add_action("take", self.take)
    
    def take(self):
        Adventure.player.current_room.pop(self.name)
        Adventure.player.money = Adventure.player.money + self.amount
        Adventure.game.do_inv()
        return True

class Wearable(Item):
    def __init__(self, name="hat", description="A silly hat", wear_msg="You put on the hat.", remove_msg="You took off the hat.", **kwargs):
        super().__init__(name, description, takeable=True, droppable=True)
        self.wear_msg = wear_msg
        self.remove_msg = remove_msg
        self.add_action("wear", self.wear)

    def wear(self):
        if Adventure.player.in_room_items(self):
           self.take()

        if self in Adventure.player.inv_items.values():
            print(self.wear_msg)
            Adventure.player.wearing[self.name] = self
            self.add_action("remove", self.remove)
            self.droppable = False
            self.remove_action("drop")
            self.remove_action("wear")
        else:
            print(f"Something wrong: couldn't wear {self.name}")
        return True

    def remove(self):
        print(self.remove_msg)
        self.remove_action("remove")
        del Adventure.player.wearing[self.name]
        self.droppable = True
        self.add_action("drop", self.drop)
        self.add_action("wear", self.wear)
        return True


class Room(Entity):
    def __init__(self, name='room', description = "An empty room", **kwargs):
        super().__init__(name, description)
        self.add_action("go", self.go)
        if 'links' in kwargs:
            for link in kwargs['links']:
                try:
                    self.link_room(Room.get(link))
                except NoEntityLinkException:
                    pass

    def go(self):
        Adventure.player.current_room.pop(Adventure.player.name)
        Adventure.player.current_room = self
        Adventure.player.current_room.add_item(Adventure.player)
        Adventure.game.current_room_intro()
        return True

    def link_room(self, room: Room):
        try:
            super().link(room)
            room.link_room(self)
        except EntityLinkException:
            pass

    def add_item(self, item: Item):
        super().link(item)

    def get_items(self, takeable_only=False):
        if takeable_only:
            return dict(filter(lambda pair : isinstance(pair[1], Item) and not pair[1].takeable == False, self.linked.items()))
        else:
            return dict(filter(lambda pair : isinstance(pair[1], Item), self.linked.items()))

    def get_rooms(self):
        return dict(filter(lambda pair : isinstance(pair[1], Room), self.linked.items()))

    def get_doors(self):
        return dict(filter(lambda pair : isinstance(pair[1], Door), self.linked.items()))

    def get_actions(self):
        actions = {}
        for item in list(self.linked.values()) + list(Adventure.player.inv_items.values()):
            for action in item.actions:
                try:
                    if not isinstance(actions[action], list):
                        actions[action] = []
                except KeyError:
                    actions[action] = []
                actions[action].append(item)

        return actions

class Door(Room):
    def __init__(self, name: str, room1: Room, room2: Room, locked = True, key: Item = None, **kwargs):
        super().__init__(name, f"Door between {room1.name} and {room2.name}")
        super().link_room(room1)
        super().link_room(room2)
        self.locked = locked
        self.key = key
        if self.locked:
            self.add_action("unlock", self.unlock)
        elif self.key != None:
            self.add_action("lock", self.lock)
        self.add_action("go", self.go)

    def get_other(self, room: Room) -> Room:
        names = list(self.linked.keys())
        if names[0] == room.name:
            return self.linked[names[1]]
        else:
            return self.linked[names[0]]
        
    # def lock(self, key):
    #     if key == self.key:
    #         self.locked = True
    #     return self.locked == True

    # def unlock(self, key):
    #     if key == self.key:
    #         self.locked = False
    #     return self.locked == False
    
    def go(self):
        if self.locked == False:
            Adventure.player.current_room.pop(Adventure.player.name)
            Adventure.player.current_room = self.get_other(Adventure.player.current_room)
            Adventure.player.current_room.add_item(Adventure.player)
            Adventure.game.current_room_intro()
        else:
            print("That door is locked.")
        return True

    def unlock(self):
        """Unlock a door"""
        if Adventure.player.in_rooms(self):
            if self.locked == False:
                print("This door is already unlocked")
            elif self.key in Adventure.player.inv_items.values():
                self.locked = False
                print("Door unlocked")
                self.remove_action("unlock")
                self.add_action("lock", self.lock)
            else:
                print("You don't have the key to unlock this door")
        else:
            print("That door isn't here")
        return True
    
    def lock(self):
        if Adventure.player.in_rooms(self):
            if self.locked == True:
                print("This door is already locked")
            elif self.key in Adventure.player.inv_items.values():
                self.locked = True
                print("Door locked")
                self.remove_action("lock")
                self.add_action("unlock", self.unlock)
            else:
                print("You don't have the key to lock this door")
        else:
            print("That door isn't here")
        return True

class Useable(Item):
    def __init__(self, name="useful item", description="A useful item", takeable=True, droppable=True, verb="use",
                 use_msg="So useful!", func=lambda: True, **kwargs):
        Item.__init__(self, name, description, takeable, droppable)
        self.use_msg = use_msg
        self.func = func
        self.add_action(verb, self.use)

    def use(self):
        print(self.use_msg)
        self.func()
        return True
    
class Eatable(Useable):
    def __init__(self, name="food", description="A tasty item", takeable=True, droppable=True, verb="eat",
                 use_msg="Yummy!", func=lambda: True, **kwargs):
        super().__init__(name, description, takeable, droppable, verb, use_msg, func)

    def use(self):
        super().use()
        try:
            # Remove the item from the player's inventory
            Adventure.player.inv_items.pop(self.name)
        except:
            pass
        return Entity.purge(self.name)

class Phone(Useable):
    def __init__(self, name="phone", description="An old phone", cost=0.25, costmsg="No service", mobile=False, **kwargs):
        super().__init__(name=name, description=description, droppable=mobile, takeable=mobile)
        self.cost = cost
        self.costmsg = costmsg
        self.add_action("use", self.use)

    def use(self, callee: str=None):
        print(f"This phone costs $ {self.cost} to use.")
        callees = dict(filter(lambda pair : pair[1].phoneable, AICharacter.get_all().items()))
        if callee == None:
            print("Who you gonna call? ", end="")
            print(list(callees.keys()))
            callee = input("(input): ")
        if callee in callees.keys():
            if Adventure.player.spend(self.cost):
                print("**RINGING**")
                callees[callee].talk(phone=True)
                print("\n*Thank you, call again.*\n")
                Adventure.game.current_room_intro()
            else:
                print(self.costmsg)
        else:
            print("You can't call them.")
        return True

class Computer(Useable):
    def __init__(self, name="computer", description="A computer", mobile=False, **kwargs):
        super().__init__(name=name, description=description, droppable=mobile, takeable=mobile)
        self.add_action("use", self.use)

    def use(self):
        print()
        print("You sit down in front of the computer, and with a flick of your hand, the console comes to life...")
        print("PRESS ENTER TO CONTINUE...", end="")
        input()
        
        os.system("clear")

        exit = "Press Ctrl+D to quit using the computer"
        quit = exit

        variables = {**globals(), **locals()}
        shell = code.InteractiveConsole(variables)
        shell.interact()

        print()
        Adventure.game.current_room_intro()
        return True

class Character(Item):
    def __init__(self, name="player", description="The main player", current_room=None, lookable=True, **kwargs):
        Item.__init__(self, name=name, description=description, droppable=False, takeable=False, lookable=lookable)

        self.current_room = None
        self.max_items = 5
        self.inv_items = {}
        self.money = float(0)
        self.inv_items = {}
        self.wearing = {}
        self.words = ""

        if current_room != None and current_room.__class__ == Room:
            self.go(current_room)

    def loopit(self):
        pass

    def in_rooms(self, room: Room):
        try:
            return room.name in list(self.current_room.get_rooms().keys())
        except:
            return False

    def in_room_items(self, item: Entity):
        try:
            return item.name in list(self.current_room.linked.keys())
        except:
            return False

    def spend(self, amount):
        if self.money >= amount:
            self.money = self.money - amount
            print('$', '{:.2f}'.format(amount), 'spent.')
#FIXME            self.do_inv()
            return amount
        else:
            print("You don't have that kind of money, peasant.")
            return
 #FIXME           return self.do_inv()

    def say(self, words="blah blah blah"):
        self.words = words

    def go(self, room = Room, check_link=True):
        if self.current_room == None or (check_link and self.in_rooms(room)) or check_link == False:
            if self.current_room != None:
                self.current_room.pop(self.name)
            self.current_room = room
            self.current_room.add_item(self)
        else:
            print("WALKER", self.name, "GO", room.name, "DIDN'T WORK")

class WalkerCharacter(Character):
    def __init__(self, name="walker", description="Just walking around", current_room=None, lookable=True, verb="greet",
                 use_msg="Hi!", func=lambda: True, **kwargs):
        Character.__init__(self, name=name, description=description, current_room=current_room, lookable=lookable)
        self.use_msg = use_msg
        self.func = func
        self.add_action(verb, self.use)
    
    def use(self):
        print(self.use_msg)
        self.func()
        return True

    def loopit(self):
        try:
            move = random.choice([True, False])
            if move:
                room = None
                while room.__class__ != Room:
                    room = random.choice(list(self.current_room.get_rooms().values()))
                #print("WALKER", self.name, "GO", room.name)
                self.go(room)
        except EntityLinkException:
            pass

class OpenAIClient():
    client = None

    @staticmethod
    def connect(api_key=""):
        if OpenAIClient.client == None:
            OpenAIClient.client = OpenAI(api_key=api_key)

    @staticmethod
    def get_or_create_assistant(name, instructions, model="gpt-3.5-turbo"):
        # Check if the assistant already exists
        assistants = OpenAIClient.client.beta.assistants.list()
        for assistant in assistants.data:
            if assistant.name == name:
                return assistant  # Return existing assistant if found

        # If not found, create a new assistant
        return OpenAIClient.client.beta.assistants.create(
            name=name,
            model=model,
            instructions=instructions,
        )

class AICharacter(Character):
    def __init__(self, name="ai character", description="Some NPC", current_room=None,
                 prompt="You are a less-than helpful, yet amusing, assistant.",
                 phone_prompt=("The user is calling you on the phone, and you answer in an amusing way. "
                               "Don't worry about sounds or actions, just generate the words."), **kwargs):
        super().__init__(name=name, description=description, current_room=current_room)
        self.phoneable = (phone_prompt != None)
        self.add_action("talk", self.talk)

        OpenAIClient.connect()
        self.assistant = OpenAIClient.get_or_create_assistant(
            name=name,
            instructions=prompt,
        )
        self.thread = OpenAIClient.client.beta.threads.create()

        if self.phoneable:
            self.phone_assistant = OpenAIClient.get_or_create_assistant(
                name=f"{name}_phone",
                instructions=f"{prompt} {phone_prompt}",
            )

            self.phone_thread = OpenAIClient.client.beta.threads.create()

    def talk(self, msg=None, phone=False):
        OpenAIClient.connect()
        thread = None
        assistant = None

        if phone and self.phoneable:
            thread = self.phone_thread
            assistant = self.phone_assistant

            OpenAIClient.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content="phone rings"
            )

        elif phone and not self.phoneable:
            print("You can't call that character.")
            return
        else:
            thread = self.thread
            assistant = self.assistant
            if msg != None:
                OpenAIClient.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=msg
                )
            else:
                last_input = input("(input): ")
                message = OpenAIClient.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=last_input
                )

        messages = None
        last_input = ""
        hangups = "bye|\*hangs up\*|\*click\*"

        while messages == None or (not re.search(hangups, messages.data[0].content[0].text.value.lower(), re.IGNORECASE) and not re.search(hangups, last_input.lower(), re.IGNORECASE)):

            run = OpenAIClient.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            if run.status == 'completed': 
                messages = OpenAIClient.client.beta.threads.messages.list(thread_id=thread.id)
                print()
                print(messages.data[0].content[0].text.value)
                if re.search(hangups, messages.data[0].content[0].text.value.lower(), re.IGNORECASE) or re.search(hangups, last_input.lower(), re.IGNORECASE):
                    if not phone:
                        Adventure.game.current_room_intro()
                    return True
                #else:
                #    print(run.status)

            last_input = input("(input): ")
            if messages != None:
                if re.search(hangups, messages.data[0].content[0].text.value.lower(), re.IGNORECASE) or re.search(hangups, last_input.lower(), re.IGNORECASE):
                    if not phone:
                        Adventure.game.current_room_intro()
                    return True
            message = OpenAIClient.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=last_input
            )


class Adventure(cmd2.Cmd):
    def __init__(self, player=None, file="world.yaml"):
        self.prompt = "> "
        self.file = file
        
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
            Adventure.player.go(list(Room.get_all().values())[0])
        else:
            print("No world file found.")

        super().__init__()

    def do_inv(self, arg=None):
        """List items in inventory"""
        print("Items you have:", list(self.player.inv_items.keys()), " --  Money: $", '{:.2f}'.format(self.player.money))

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
        for action_item in self.player.current_room.get_actions()[action]:
            items.append(action_item.name)
        return [i for i in items if i.startswith(item)]

    def get_all_commands(self):
        return list(self.player.current_room.get_actions().keys()) + ['exit', 'help', 'inv', 'reset', 'where']

    def default(self, line):
        command = shlex.split(line.raw)
        try:
            item = Entity.get(command[1].lower())
            action = command[0].lower()
            if self.player.in_room_items(item) or item in self.player.inv_items.values():
                if not item.do(action):
                    print("I don't know how to do that")
            else:
                print("I don't know how to do that")
        except:
            print("I don't know how to do that")
        
    def current_room_intro(self):
        for char in dict(filter(lambda pair : self.player.in_room_items(pair[1]), Character.get_all().items())).values():
            char.loopit()
        print('You are in:', self.player.current_room.name.upper(), ' -- ', self.player.current_room.description)
        print('In this room, there are:', list(dict(filter(lambda pair : pair[1] != self.player, self.player.current_room.get_items().items())).keys()))
        print('The rooms next door:', list(self.player.current_room.get_rooms().keys()))
        print()
        for char in dict(filter(lambda pair : self.player.in_room_items(pair[1]) and pair[1] != self.player, Character.get_all().items())).values():
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
    Adventure.player = Character(lookable=False)
    Adventure.game = Adventure(Adventure.player)
    Adventure.game.cmdloop()
