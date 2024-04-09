from __future__ import annotations
import cmd2, code, os, random, re, shlex
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
    def __init__(self, name = 'item', description = "No description", droppable=True, takeable=True, lookable=True):
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
            del Adventure.player.inv_items[self.name]
            Adventure.player.current_room.add_item(self)
            self.remove_action("drop")
            if self.takeable:
                self.add_action("take", self.take)
            Adventure.game.do_inv()
        else:
            print("You don't have that item, dingus")
        return True

#class VendingMachine(Item):
#class Phone(Item):

class Money(Item):
    def __init__(self, name="money", description="some money", amount=1.00):
        super().__init__(name, description, droppable=False)
        self.amount = amount
        self.add_action("take", self.take)
    
    def take(self):
        Adventure.player.current_room.pop(self.name)
        Adventure.player.money = Adventure.player.money + self.amount
        Adventure.game.do_inv()
        return True

class Wearable(Item):
    def __init__(self, name="hat", description="A silly hat", wear_msg="You put on the hat.", remove_msg="You took off the hat."):
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
    def __init__(self, name='room', description = "An empty room"):
        super().__init__(name, description)
        self.add_action("go", self.go)

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
    def __init__(self, name: str, room1: Room, room2: Room, locked = True, key: Item = None):
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
                 use_msg="So useful!", func=lambda: True):
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
                 use_msg="Yummy!", func=lambda: True):
        super().__init__(name, description, takeable, droppable, verb, use_msg, func)

    def use(self):
        super().use()
        try:
            Adventure.player.inv_items.remove(self)
        except:
            pass
        return Entity.purge(self.name)

class Phone(Useable):
    def __init__(self, name="phone", description="An old phone", cost=0.25, costmsg="No service", mobile=False):
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
    def __init__(self, name="computer", description="A computer", mobile=False):
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
    def __init__(self, name="player", description="The main player", current_room=None, lookable=True):
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
                 use_msg="Hi!", func=lambda: True):
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
                               "Don't worry about sounds or actions, just generate the words.")):
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
    def __init__(self, player=None):
        self.prompt = "> "
        self.file = None
        
        living_room = Room("living room", "A dingy living room with old furniture, yuck i hope someone cleans it")
        dining_room = Room("dining room", "This dining room sucks. I think that's 100 year old food on the table")
        kitchen = Room("kitchen", "This kitchen is so old and nasty, the flies died 50 years ago.")
        hallway = Room("hallway", "A dimly lit hallway which smells of dusty, old ladies and roten cheese")
        bathroom = Room("bathroom", "I really don't have to poop anymore, guys...")
        garden = Room("garden", "a very dead garden,yuck and one mysterious gold flower")
        sidewalk = Room("sidewalk", "It's not much to look at, but it gets your feet places.")

        living_room.link_room(hallway)
        living_room.link_room(dining_room)
        hallway.link_room(dining_room)
        hallway.link_room(bathroom)
        dining_room.link_room(kitchen)
        sidewalk.link_room(garden)
            
        paintbrush = Useable("paintbrush", "A very old, antique paintbrush. Looks like it was used by a big ol' hippy.",
                             use_msg="OMG LOOK, A BIG OL' HIPPY!", func=lambda: setattr(Adventure.player, "big_ol_hippy", True))
        pillow = Item("pillow", "this is so yellow my eyes could burn")
        old_hot_dog = Eatable("old hot dog", "It has a weird little kink in it, like someone tried to bite it a long time ago.",
                              use_msg=("You somehow manage to choke down a 300 year old, all beef hot dog. Were it not for your "
                              "well-lubricated esophagus, you would be dead right now. Let's hope you don't get food poisoning "
                              "or become a zombified, hot dog person. Nasty."))
        spoon = Useable("spoon", "A little crusty, but if you lick it and wipe it on your shirt, it might get shiny.", verb="lick",
                        use_msg="Did you like that? Was it satisfying for you?")
        pan = Item("pan", "Encrusted with supper from long, long ago")
        knife = Item("knife", "It's duller than a bag of rocks. Still, somebody will cut themselves with this.")
        candlestick = Item("candlestick", "So burned I think someone has used this so many times")
        wig = Wearable("wig", "This might have scabies; maybe I should not wear it",
                       wear_msg="You put on the wig. Somehow it makes you look even weirder.",
                       remove_msg="You finally took that thing off?? It's about dang time, man...")
        shiny_knob = Item("shiny knob", "Honestly, this is the best thing you\'ve seen in your life im crying right now", takeable=False, droppable=False)
        shoe = Wearable("shoe", "Right, 10 1/2 wide",
                        wear_msg="You try like the most graceful of Cinderella's evil step-sisters to squeeze the shoe on your foot. You exclaim: \"IT FITS!\"",
                        remove_msg="OH MY GOODNESS, FINALLY! Your foot throbs an aching cadence of relief.")
        book = Useable("book", "A very olde booke of joke magical incantations.", verb="read",
                       use_msg="You open the book to a random spot, and read this:\n", func=lambda: os.system("fortune"))
        gold_flower = Item("gold flower", "An odd flower that's golden. It smells like pee.")
        hose = Useable("hose", "A very drippy old hose. That water is brown, and what is that smell??", verb="drink",
                       use_msg=("You guzzle the brown stuff from the hose and tell yourself it was chocolate milk! Even as "
                                "you bask in the glory of chocolate milk, your stomach gets very queasy. Then you throw up. "
                                "Good job."))
        toilet = Item("toilet", "This toilet once stood as an art installation at the Metropolitan Museum of Art. Look at it now...")
        bathtub = Item("bathtub", "Imagine the first person who sees you carrying this out of the house, just look at their face!")
        computer = Computer("computer", "Would you look at that?! A computer! It looks really old, but it's running...", mobile=False)
        payphone = Phone("payphone", "It's an old pay phone! You might need to get some change to make a call.", cost=0.25, costmsg="Come back with some quarters next time.")
        cellphone = Phone("cell phone", "It's an old cell phone! I wonder if it has any service...", cost=0.01, costmsg="No money, no phone service!", mobile=True)
        quarters = Money("quarters", "Oooh, a pile of quarters!", amount=2.25)
        key = Item("key", "A rather shiny key")

        front_door = Door("front door", hallway, garden, locked=True, key=key)

        living_room.add_item(paintbrush)
        living_room.add_item(book)
        living_room.add_item(computer)
        dining_room.add_item(old_hot_dog)
        dining_room.add_item(spoon)
        dining_room.add_item(cellphone)
        kitchen.add_item(pan)
        kitchen.add_item(knife)
        kitchen.add_item(quarters)
        hallway.add_item(candlestick)
        hallway.add_item(wig)
        hallway.add_item(shoe)
        bathroom.add_item(toilet)
        bathroom.add_item(bathtub)
        bathroom.add_item(key)
        garden.add_item(gold_flower)
        garden.add_item(hose)
        sidewalk.add_item(payphone)

        if player == None:
            self.player = Character()
        else:
            self.player = player
        self.player.go(Room.get("living room"))

        cat = WalkerCharacter(name="cat", description="There's a cat, sleek and black.", current_room=Room.get("living room"),
                              verb="pet", use_msg="*PURRRR*")

        old_man = AICharacter(name="old man", description="There's a crotchety, old man. He doesn't seem to be in a good mood.", 
                              prompt=("You are a crotchety old man, and a terrible conversationalist. You hate to be interrupted, "
                                      "even though you're never doing anything important."),
                              phone_prompt=("The user is calling you on the phone, and you answer in a very amusing way. Don't worry about "
                                            "sounds or actions, just generate the man's words. Sometimes he randomly hangs up."))
        kitchen.add_item(old_man)

        carl = AICharacter(name="carl", description="Oh, there's Carl...",
                           prompt=("You are a happy-go-lucky but thoroughly dense young chap named Carl. You are a friend, not an assistant. You "
                                   "sometimes forget what you're talking about. You try very hard to not talk about turtles, but sometimes "
                                   "you can't help yourself. Your mental bandwidth is frighteningly scarce."))
        sidewalk.add_item(carl)


        super().__init__()

    def help_use(self):
        print("Use an item, some items are useful!")

    def help_eat(self):
        print("Once in a while, you might want to eat something.")

    def help_wear(self):
        print("A wearable item, you might like to wear it.")

    def help_remove(self):
        print("If you put something on, sometime you may want to take it off.")

    def help_read(self):
        print("You might find something worth reading.")

    def help_lick(self):
        print("Ewww, don't put that in your mouth. Unless you know it's tasty. Maybe just lick it...")

    def help_drink(self):
        print("Maybe you'll find a cool, refreshing beverage.")

    def help_pet(self):
        print("Have you ever been on a quest without something cute and furry showing up?")

    def help_talk(self):
        print("Everybody needs somebody sometimes!")

    def help_go(self):
        print("Go where you wanna go, yo.")

    def help_look(self):
        print("Look at an item; the description is probably funny.")

    def help_take(self):
        print("You can take some items into your inventory. Beware of cursed and/or stinky items.")

    def help_drop(self):
        print("You can drop most items from your inventory. Unless you're wearing them.")

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
