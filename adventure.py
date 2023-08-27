from __future__ import annotations
import cmd, code, os

class EntityLinkException(Exception):
    "Thrown when there is already an Entity with this name"

class NoEntityLinkException(Exception):
    "Thrown when there is no near-enough link to an Entity with this name"

class Entity:
    world = None;

    def __init__(self, name = 'No name', description = 'No description'):
        self.name = name
        self.description = description
        self.linked = {}

        if Entity.world != None:
            Entity.world.link(self)

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
    def __init__(self, name = 'item', description = "No description", droppable=True, takeable=True):
        super().__init__(name, description)
        self.actions = {}
        self.droppable = droppable
        self.takeable = takeable

    def add_item(self, item: Item):
        super().link(item)

    def add_action(self, name = "use", function = lambda: True):
        self.actions[name] = function

    def do(self, action):
        try:
            return self.actions[action]()
        except KeyError:
            return None

#class VendingMachine(Item):
#class Phone(Item):

class Money(Item):
    def __init__(self, name="money", description="some money", amount=1.00):
        super().__init__(name, description, droppable=False)
        self.amount = amount

class Room(Entity):
    def __init__(self, name='room', description = "An empty room"):
        super().__init__(name, description)

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
            return dict(filter(lambda pair : (isinstance(pair[1], Item) or isinstance(pair[1], Money)) and not pair[1].takeable == False, self.linked.items()))
        else:
            return dict(filter(lambda pair : isinstance(pair[1], Item) or isinstance(pair[1], Money), self.linked.items()))

    def get_rooms(self):
        return dict(filter(lambda pair : isinstance(pair[1], Room) or isinstance(pair[1], Door), self.linked.items()))

    def get_doors(self):
        return dict(filter(lambda pair : isinstance(pair[1], Door), self.linked.items()))

    def get_actions(self):
        actions = {}
        for item in self.get_items().values():
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

    def get_other(self, room: Room) -> Room:
        names = list(self.linked.keys())
        if names[0] == room.name:
            return self.linked[names[1]]
        else:
            return self.linked[names[0]]
        
    def lock(self, key):
        if key == self.key:
            self.locked = True
        return self.locked == True

    def unlock(self, key):
        if key == self.key:
            self.locked = False
        return self.locked == False

class Adventure(cmd.Cmd):
    def __init__(self):
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
        
        paintbrush = Item("paintbrush", "A very old, antique paintbrush. Looks like it was used by a big ol' hippy.")
        pillow = Item("pillow", "this is so yellow my eyes could burn")
        old_hot_dog = Item("old hot dog", "It has a weird little kink in it, like someone tried to bite it a long time ago.")
        spoon = Item("spoon", "A little crusty, but if you lick it and wipe it on your shirt, it might get shiny.")
        pan = Item("pan", "Encrusted with supper from long, long ago")
        knife = Item("knife", "It's duller than a bag of rocks. Still, somebody will cut themselves with this.")
        candlestick = Item("candlestick", "So burned I think someone has used this so many times")
        wig = Item("wig", "This might have scabies; maybe I should not wear it")
        shiny_knob = Item("shiny knob", "Honestly, this is the best thing you\'ve seen in your life im crying right now", takeable=False, droppable=False)
        shoe = Item("shoe", "Right, 10 1/2 wide")
        book = Item("book", "A very olde booke of joke magical incantations.")
        gold_flower = Item("gold flower", "An odd flower that's golden. It smells like pee.")
        hose = Item("hose", "A very drippy old hose. That water is brown, and what is that smell??")
        toilet = Item("toilet", "This toilet once stood as an art installation at the Metropolitan Museum of Art. Look at it now...")
        bathtub = Item("bathtub", "Imagine the first person who sees you carrying this out of the house, just look at their face!")
        computer = Item("computer", "Would you look at that?! A computer! It looks really old, but it's running...", takeable=False, droppable=False)
        phone = Item("phone", "It's an old pay phone! You might need to get some change to make a call.", takeable=False, droppable=False)
        quarters = Money("quarters", "Oooh, a pile of quarters!", amount=2.25)
        key = Item("key", "A rather shiny key")

        front_door = Door("front door", hallway, garden, locked=True, key=key)

        paintbrush.add_action("use", self.use_paintbrush)
        computer.add_action("use", self.use_computer)
        phone.add_action("use", self.use_phone)
        old_hot_dog.add_action("eat", self.eat_old_hot_dog)
        wig.add_action("wear", self.wear_wig)
        wig.add_action("remove", self.remove_wig)
        book.add_action("read", self.read_book)
        spoon.add_action("lick", self.lick_spoon)
        hose.add_action("drink", self.drink_hose)

        living_room.add_item(paintbrush)
        living_room.add_item(book)
        living_room.add_item(computer)
        dining_room.add_item(old_hot_dog)
        dining_room.add_item(spoon)
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
        sidewalk.add_item(phone)

        self.max_items = 5
        self.inv_items = {}
        self.money = float(0)

        self.current_room = living_room
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

    def do_use(self, item):
        return self.default(f"use {item}")
    def do_eat(self, item):
        return self.default(f"eat {item}")
    def do_wear(self, item):
        return self.default(f"wear {item}")
    def do_remove(self, item):
        return self.default(f"remove {item}")
    def do_read(self, item):
        return self.default(f"read {item}")
    def do_lick(self, item):
        return self.default(f"lick {item}")
    def do_drink(self, item):
        return self.default(f"drink {item}")

    def in_rooms(self, room: Room):
        try:
            return room.name in list(self.current_room.get_rooms().keys())
        except:
            return False

    def in_room_items(self, item: Item):
        try:
            return item.name in list(self.current_room.get_items().keys())
        except:
            return False

    def spend(self, amount):
        if self.money >= amount:
            self.money = self.money - amount
            print('$', '{:.2f}'.format(amount), 'spent.')
            self.do_inv()
            return amount
        else:
            print("You don't have that kind of money, peasant.")
            return self.do_inv()

    def do_go(self, name: str):
        """Go from one room to another"""
        try:
            room = Room.get(name)
        except NoEntityLinkException:
            try:
                door = Door.get(name)
            except NoEntityLinkException:
                print("That room doesn't exist")
                return False

        if self.in_rooms(room):
            if isinstance(room, Door):
                if room.locked:
                    print("That door is locked")
                    return False
                else:
                    self.current_room = room.get_other(self.current_room)
                    self.current_room_intro()
            else:
                self.current_room = room
                self.current_room_intro()
        else:
            print("That room isn't next door!")
            return False

    def complete_go(self, text, line, begidx, endidx):
        return [i for i in self.current_room.get_rooms().keys() if i.startswith(text)]
    
    def do_unlock(self, name: str):
        """Unlock a door"""
        try:
            door = Door.get(name)
        except NoEntityLinkException:
            print("That door doesn't exist")
            return False

        if self.in_rooms(door):
            if door.locked == False:
                print("This door is already unlocked")
            elif door.key in self.inv_items.values():
                door.locked = False
                print("Door unlocked")
            else:
                print("You don't have the key to unlock this door")
        else:
            print("That door isn't here")

    def complete_unlock(self, text, line, begidx, endidx):
        return [i for i in self.current_room.get_doors().keys() if i.startswith(text)]

#    def do_traverse(self, name: str):
#        print(Entity.world.get_linked(name).traverse(1))
            
    def do_take(self, name: str):
        """Take an item"""
        try:
            item = Money.get(name)
            self.current_room.pop(name)
            self.money = self.money + item.amount
            return self.do_inv()
        except:
            try:
                item = Item.get(name)
            except:
                print("That item doesn't exist")
                return False
            
        if self.in_room_items(item):
            if len(self.inv_items) >= self.max_items:
                print(f"You already have {self.max_items} items, buddy")
            elif not item.takeable:
                print("You can't take that, what are you thinking??")
            else:
                self.inv_items[name] = self.current_room.pop(name)
                self.do_inv()
        else:
            print("That item is not in this room!")

    def complete_take(self, text, line, begidx, endidx):
        return [i for i in self.current_room.get_items(takeable_only=True).keys() if i.startswith(text)]

    def do_drop(self, name: str):
        """Drop an item from inventory"""
        try:
            item = Item.get(name)
            if item in self.inv_items.values():
                if item.droppable:
                    del self.inv_items[name]
                    self.current_room.add_item(item)
                    self.do_inv()
                else:
                    print("You can't drop that right now!")
            else:
                print("You don't have that item, dingus")
        except KeyError:
            print("That item doesn't exist")
        except NoEntityLinkException:
            print("That item doesn't exist")

    def complete_drop(self, text, line, begidx, endidx):
        items = [i for i in self.inv_items]
        droppable = []
        for item in items:
            item = Item.get(item)
            if item.droppable != False:
                droppable.append(item.name)
        return [i for i in droppable if i.startswith(text)]

    def do_inv(self, arg=None):
        """List items in inventory"""
        print("Items you have:", list(self.inv_items.keys()), " --  Money: $", '{:.2f}'.format(self.money))

    def do_look(self, name: str):
        """Look at an item"""
        try:
            item = Item.get(name)
            if item in self.inv_items or self.in_room_items(item):
                print(name.upper(), " -- " , item.description)
            else:
                print("That item isn't here")
        except NoEntityLinkException:
            print("That item doesn't exist")

    def complete_look(self, text, line, begidx, endidx):
        return [i for i in self.current_room.get_items().keys() if i.startswith(text)]

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
        command = line.split(' ', 1)
        item = command[1].lower()
        action = command[0].lower()
        items = []
        for action_item in self.current_room.get_actions()[action]:
            items.append(action_item.name)
        return [i for i in items if i.startswith(item)]

    def default(self, line):
        def unknown():
            try:
                room = Room.get(line)
                if self.in_rooms(room):
                    return self.do_go(line)
            except NoEntityLinkException:                
                print("I don't know how to do that")
            
        command = line.split(' ', 1)
        try:
            item = Item.get(command[1].lower())
            action = command[0].lower()

            if not item.do(action):
                unknown()
        except:
            unknown()
        
    def current_room_intro(self):
        print('You are in:', self.current_room.name.upper(), ' -- ', self.current_room.description)
        print('In this room, there are:', list(self.current_room.get_items().keys()))
        print('The rooms next door:', list(self.current_room.get_rooms().keys()))

    def preloop(self):
        print("Welcome to the adventure game!   Type help or ? to list commands.\n")
        self.current_room_intro()

    def use_paintbrush(self):
        print("OMG LOOK, A BIG OL' HIPPY!")
        self.big_ol_hippy = True
        return True

    def use_computer(self):
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
        self.current_room_intro()
        return True

    def use_phone(self):
        print("This phone costs $ 0.25 cents to use.")
        if self.spend(0.25):
            print("Thank you, call again.")
        else:
            print("Come back with some quarters next time.")
        return True

    def wear_wig(self):
        wig = Item.get("wig")
        if self.in_room_items(wig):
            self.do_take("wig")

        if wig in self.inv_items.values():
            print("You put on the wig. Somehow it makes you look even weirder.")
            self.wearing_wig = True
            Entity.world.get("wig").droppable = False
            return True
        else:
            print("Couldn't put wig in inventory")
            raise OSError

    def remove_wig(self):
        print("You finally took that thing off?? It's about dang time, man...")
        self.wearing_wig = False
        Entity.world.get("wig").droppable = True
        return True

    def eat_old_hot_dog(self):
        print("You somehow manage to choke down a 300 year old, all beef hot dog. Were it not for your well-lubricated esophagus, you would be dead right now. Let's hope you don't get food poisoning or become a zombified, hot dog person. Nasty.")
        try:
            self.inv_items.remove(Item.get('old hot dog'))
        except:
            pass
        return Entity.purge('old hot dog')

    def read_book(self):
        print("You open the book to a random spot, and read this:\n")
        os.system("fortune")
        return True
        
    def lick_spoon(self):
        print("Did you like that? Was it satisfying for you?")
        return True
        
    def drink_hose(self):
        print("You guzzle the brown stuff from the hose and tell yourself it was chocolate milk! Even as you bask in the glory of chocolate milk, your stomach gets very queasy. Then you throw up. Good job.")
        return True

if __name__ == '__main__':    
    Adventure.game = Adventure()
    Adventure.game.cmdloop()
