from __future__ import annotations
import random, re
from openai import OpenAI
from entities import Room, Item, Entity, EntityLinkException

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
                        Entity.game.current_room_intro()
                    return True
                #else:
                #    print(run.status)

            last_input = input("(input): ")
            if messages != None:
                if re.search(hangups, messages.data[0].content[0].text.value.lower(), re.IGNORECASE) or re.search(hangups, last_input.lower(), re.IGNORECASE):
                    if not phone:
                        Entity.game.current_room_intro()
                    return True
            message = OpenAIClient.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=last_input
            )

