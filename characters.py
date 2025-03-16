from __future__ import annotations
import random, re, os
import openai
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

class NonPlayerCharacter(Character):
    def __init__(self, name="npc", description="Just hanging around", current_room=None, lookable=True, verb="greet",
                 use_msg="Hi!", func=lambda var=None: True, **kwargs):
        Character.__init__(self, name=name, description=description, current_room=current_room, lookable=lookable)
        self.use_msg = use_msg
        self.func = func
        self.add_action(verb, self.use)
    
    def use(self):
        if self.use_msg != None:
            print(self.use_msg)
        self.func(self)
        return True

    def loopit(self):
        pass

class WalkerCharacter(NonPlayerCharacter):
    def __init__(self, name="walker", description="Just walking around", current_room=None, lookable=True, verb="greet",
                 use_msg="Hi!", func=lambda var=None: True, **kwargs):
        NonPlayerCharacter.__init__(self, name=name, description=description, current_room=current_room, lookable=lookable, verb=verb, use_msg=use_msg, func=func)

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
    assistants = None

    @staticmethod
    def connect(api_key=os.getenv("OPENAI_API_KEY")):
        if OpenAIClient.client == None:
            OpenAIClient.client = openai.OpenAI(api_key=api_key)
        openai.api_key = api_key

    @staticmethod
    def get_or_create_assistant(name, instructions, model="gpt-4-turbo"):
        # Check if the assistant already exists
        if OpenAIClient.assistants == None:
            OpenAIClient.assistants = OpenAIClient.client.beta.assistants.list()
        for assistant in OpenAIClient.assistants.data:
            if assistant.name == name:
                return assistant  # Return existing assistant if found

        # If not found, create a new assistant
        assistant = OpenAIClient.client.beta.assistants.create(
            name=name,
            model=model,
            instructions=instructions,
        )
        OpenAIClient.assistants = OpenAIClient.client.beta.assistants.list()

    @staticmethod
    def oneoff_prompt(prompt, model="gpt-4-turbo"):
        OpenAIClient.connect()
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content

class AICharacter(Character):
    def __init__(self, name="ai character", description="Some NPC", current_room=None,
                 prompt="You are a less-than helpful, yet amusing, assistant.",
                 phone_prompt=("The user is calling you on the phone, and you answer in an amusing way. "
                               "Don't worry about sounds or actions, just generate the words."),
                 func=lambda json: print(f"Character returned: {json}"), **kwargs):
        super().__init__(name=name, description=description, current_room=current_room)
        self.phoneable = (phone_prompt != None)
        self.func = func
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

        thread = self.phone_thread if phone and self.phoneable else self.thread
        assistant = self.phone_assistant if phone and self.phoneable else self.assistant

        if phone and not self.phoneable:
            print("You can't call that character.")
            return

        user_message = "phone rings" if phone else msg

        if user_message is None:
            user_message = input("(input): ")

        OpenAIClient.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        hangups = r"bye|\*hangs up\*|\*click\*"

        run_stream = OpenAIClient.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
            stream=True
        )

        full_message = ""
        display_stream = True

        print("\nCharacter response:", end="\n\n")

        for event in run_stream:
            if event.event == 'thread.message.delta':
                for delta in event.data.delta.content:
                    if delta.type == 'text':
                        chunk = delta.text.value
                        full_message += chunk
                        display_stream = (full_message.count('```') % 2 == 0)
                        if display_stream:
                            print(chunk, end="", flush=True)

        print("\n")

        message_stripped = replace_triple_backticks(full_message)
        json_obj = find_json_objects(full_message)

        if len(json_obj) > 0:
            self.func(json_obj[0])
            return True
        elif message_stripped != full_message and len(json_obj) < 1:
            print(f"ERROR: assistant provided object but it wasn't picked up:\n\n{full_message}")

        if re.search(hangups, full_message.lower(), re.IGNORECASE) or re.search(hangups, user_message.lower(), re.IGNORECASE):
            if not phone:
                Entity.game.current_room_intro()
            return True
        else:
            return self.talk(phone=phone)

    def add_to_prompt(self, new_instructions: str):
        """
        Insert a 'system' message into the existing thread,
        effectively updating the context for subsequent calls.
        """
        if not hasattr(self, 'thread') or self.thread is None:
            print("No active thread to update.")
            return

        # We create a new system message in the same thread
        OpenAIClient.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=f"(System Update): {new_instructions}"
        )

def find_json_objects(text: str):
    """
    Tries to find and parse *all* JSON objects in `text` by scanning from left to right.
    Returns a list of tuples (parsed_obj, start_index, end_index).
    """
    import json
    decoder = json.JSONDecoder()
    results = []

    i = 0
    n = len(text)

    while i < n:
        # Skip ahead until we see a '{' (or '[' if we also want arrays).
        # If you're only expecting objects, scan for '{'—if arrays too, look for '[' as well.
        if text[i] not in ['{', '[']:
            i += 1
            continue

        try:
            parsed_obj, end_index = decoder.raw_decode(text, i)
            # If we get here, it successfully parsed a JSON object
            results.append(parsed_obj)
            i = end_index  # jump past this object
        except json.JSONDecodeError:
            i += 1  # not valid JSON here, move on

    return results

def replace_triple_backticks(text: str, replacement: str='') -> str:
    """
    Replaces all substrings enclosed by triple backticks (``` ... ```) with a specified replacement string.

    :param text: The original string that may contain triple-backtick blocks.
    :param replacement: The string to replace triple-backtick blocks with.
    :return: The string with all triple-backtick blocks replaced.
    """
    # DOTALL flag so '.' matches newlines as well
    return re.sub(r'```.*?```', replacement, text, flags=re.DOTALL)