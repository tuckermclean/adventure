from __future__ import annotations
import code, os
from entities import Item, Entity
from characters import Character, AICharacter, WalkerCharacter, NonPlayerCharacter

#class VendingMachine(Item):
#class Phone(Item):

class Money(Item):
    def __init__(self, name="money", description="some money", amount=1.00, **kwargs):
        super().__init__(name, description, droppable=False)
        self.amount = amount
        self.add_action("take", self.take)
    
    def take(self, **kwargs):
        Entity.player.current_room.pop(self.name)
        Entity.player.money = Entity.player.money + self.amount
        Entity.game.current_room_intro()
        return True

class Wearable(Item):
    def __init__(self, name="hat", description="A silly hat", wear_msg="You put on the hat.", remove_msg="You took off the hat.", **kwargs):
        super().__init__(name, description, takeable=True, droppable=True)
        self.wear_msg = wear_msg
        self.remove_msg = remove_msg
        self.add_action("wear", self.wear)

    def wear(self):
        if Entity.player.in_room_items(self):
           self.take()

        if self in Entity.player.inv_items.values():
            print(self.wear_msg)
            Entity.player.wearing[self.name] = self
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
        del Entity.player.wearing[self.name]
        self.droppable = True
        self.add_action("drop", self.drop)
        self.add_action("wear", self.wear)
        return True

class Useable(Item):
    def __init__(self, name="useful item", description="A useful item", takeable=True, droppable=True, verb="use",
                 use_msg=None, func=lambda var=None: True, **kwargs):
        Item.__init__(self, name, description, takeable=takeable, droppable=droppable)
        self.use_msg = use_msg
        self.func = func
        self.verb = verb
        self.add_action(verb, self.use)

    def use(self):
        if self.use_msg != None:
            print(self.use_msg)
        self.func(self)
        return True

class Weapon(Useable):
    def __init__(self, name="weapon", description="A weapon", damage=1, **kwargs):
        super().__init__(name=name, description=description, **kwargs)
        self.damage = damage
        self.add_action("use", self.use)

    def use(self, target=None):
        if target == None:
            target = Character.get(input(f"Who do you want to hit? {list(dict(filter(lambda pair : type(pair[1]) in [Character, AICharacter, WalkerCharacter, NonPlayerCharacter], Entity.player.current_room.get_items().items())).keys())}: "))
        elif type(target) == str:
            target = Character.get(target)

        if type(target) in [Character, AICharacter, WalkerCharacter, NonPlayerCharacter]:
            target.take_damage(self.damage)
        else:
            print("You can only use this weapon on a character.")
        return True

class Eatable(Useable):
    def __init__(self, name="food", description="A tasty item", takeable=True, droppable=True, verb="eat",
                 use_msg="Yummy!", func=lambda var=None: True, **kwargs):
        super().__init__(name, description, takeable, droppable, verb, use_msg, func)

    def use(self):
        super().use()
        try:
            # Remove the item from the player's inventory
            Entity.player.inv_items.pop(self.name)
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
            if Entity.player.spend(self.cost):
                print("**RINGING**")
                callees[callee].talk(phone=True)
                print("\n*Thank you, call again.*\n")
                Entity.game.current_room_intro()
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
        Entity.game.current_room_intro()
        return True
