import cmd

class Adventure(cmd.Cmd):
    def __init__(self):
        self.prompt = "> "
        self.file = None
        self.items = {
            'paintbrush': {
                'description': 'A very old, antique paintbrush. Looks like it was used by a big ol\' hippy.'
                },
            'pillow': {
                'description': ' this is so yellow my eyes could burn'
                },
            'old hot dog': {
                'description': 'It has a weird little kink in it, like someone tried to bite it a long time ago.'
                },
            'spoon': {
                'description': 'A little crusty, but if you lick it and wipe it on your shirt, it might get shiny.'
                },
            'pan': {
                'description': 'Encrusted with supper from long, long ago'
                },
            'knife': {
                'description': 'It\'s duller than a bag of rocks. Somebody will cut themselves with this.'
                },
            'candlestick': {
                'description': 'so bernd i think someone has used this so many times'
                },
            'old wig': {
                'description': 'This might have scabies maybe i should not wear it'
                },
            'shiny knob': {
                'description': 'Honestly, this is the best thing you\'ve seen in your life im crying right now'
                },
            'shoe': {
                'description':'Right, 10 1/2 wide'
                },
            'book': {
                'description': 'A very olde booke of joke magical incantations.'
                },
            'flower': {
                'description': 'a odd flower thats golden. It smells like pee.'
                },
            'hose': {
                'description': 'a very drippy old hose, that water is brown and what is that smell??'
                },
            'toilet': {
                'description': 'This toilet once stood as an art installation at the Metropolitan Museum of Art. Look at it now...'
                },
            'bathtub': {
                'description': 'Imagine the first person who sees you carrying this out of the house, just look at their face!'
                },
    #        'book': {
    #            'description': 'A very olde booke of joke magical incantations.'
    #            },
            }
        
        self.rooms = {
            'living room': {
                'description': 'A dingy living room with old furniture, yuck i hope someone cleans it',
                'items': ['paintbrush','pillow'],
                'rooms': ['hallway','garden']
                },
            'dining room': {
                'description': 'This dining room sucks. I think that\'s 100 year old food on the table',
                'items': ['old hot dog','spoon'],
                'rooms': ['hallway', 'kitchen','garden']
                },
            'kitchen': {
                'description': 'This kitchen is so old and nasty, the flies died 50 years ago.',
                'items': ['pan', 'knife'],
                'rooms': ['dining room','garden']
                },
            'hallway': {
                'description': 'A dimly lit hallway which smells of dusty, old ladies and roten cheese',
                'items': ['candlestick', 'old wig'],
                'rooms': ['living room', 'dining room', 'locked door', 'bathroom']
                },
            'bathroom': {
                'description': 'I really don\'t have to poop anymore, guys...',
                'items': ['toilet', 'bathtub'],
                'rooms': ['hallway'],
                },
            'garden': {
                'description': 'a very dead garden,yuck and one mysterious alive flower',
                'items': ['flower', 'hose'],
                'rooms': ['living room','dining room','kitchen']
                },
            'locked door': {
                'description': 'A very mysterious locked door stands before you and to pears?',
                'items': ['shiny knob', 'shoe', 'book'],
                'rooms': ['hallway']
                },
    #        'locked door': {
    #            'description': 'A very mysterious locked door stands before you and to pears?',
    #            'items': ['shiny knob', 'shoe', 'book'],
    #            'rooms': ['hallway']
    #            },
            }
        self.max_items = 5
        self.inv_items = []

        self.current_room = 'living room'
        super().__init__()

    def in_rooms(self, room):
        if room in self.rooms[self.current_room]['rooms']:
            return True
        else:
            return False

    def in_room_items(self, item):
        if item in self.rooms[self.current_room]['items']:
            return True
        else:
            return False
        
    def do_go(self, room):
        if self.in_rooms(room):
            self.current_room = room
            self.current_room_intro()
        else:
            print("That room isn't next door!")
            
    def do_take(self, item):
        if self.in_room_items(item):
            if len(self.inv_items) >= 5:
                print("You already have 5 items, buddy")
            else:
                self.rooms[self.current_room]['items'].remove(item)
                self.inv_items.append(item)
                self.do_inv()
        else:
            print("That item is not in this room!")

    def do_drop(self, item):
        if item in self.inv_items:
            self.inv_items.remove(item)
            self.rooms[self.current_room]['items'].append(item)
            self.do_inv()
        else:
            print("You don't have that item, dingus")

    def do_inv(self, arg=None):
        print("Items you have:", self.inv_items)

    def do_look(self, item):
        if item in self.inv_items or self.in_room_items(item):
            print(item.upper(), " -- " , self.items[item]["description"])
        else:
            print("That item isn't here")

    def do_where(self, arg=None):
        self.current_room_intro()

    def do_exit(self, arg=None):
        quit()

    def do_reset(self, arg=None):
        self.postloop()
        Adventure().cmdloop()

    def postloop(self):
        return True
    
    def default(self, line):
        print("I don't know how to do that")
        
    def current_room_intro(self):
        print('You are in:', self.current_room.upper(), ' -- ', self.rooms[self.current_room]['description'])
        print('In this room, there are:', self.rooms[self.current_room]['items'])
        print('The rooms next door:', self.rooms[self.current_room]['rooms'])

    def preloop(self):
        print("Welcome to the adventure game!   Type help or ? to list commands.\n")
        self.current_room_intro()
        
if __name__ == '__main__':
    
    Adventure().cmdloop()
    
help
