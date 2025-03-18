# gui_adventure.py

import tkinter as tk
from tkinter import messagebox, simpledialog
from characters import Character, AICharacter
from entities import Entity, Room, Door
from adventure import Adventure
import sys
import threading

class AdventureGUI:
    def __init__(self, root, adventure_game):
        self.root = root
        self.game = adventure_game
        self.player = Entity.player

        self.root.title("Adventure Game")
        self.root.geometry('800x600')

        self.selected_action = None
        self.selected_item = None

        self.create_widgets()
        self.redirect_stdout()
        self.update_gui()

    def create_widgets(self):
        self.location_label = tk.Label(self.root, text="", font=("Helvetica", 16, "bold"))
        self.location_label.pack(pady=5)

        self.location_desc = tk.Label(self.root, text="", wraplength=500, justify="left")
        self.location_desc.pack(pady=5)

        self.action_buttons_frame = tk.Frame(self.root)
        self.action_buttons_frame.pack(pady=5)

        self.item_buttons_frame = tk.Frame(self.root)
        self.item_buttons_frame.pack(pady=5)

        self.adjacent_rooms_frame = tk.Frame(self.root)
        self.adjacent_rooms_frame.pack(pady=5)

        self.inventory_frame = tk.Frame(self.root)
        self.inventory_frame.pack(pady=5)

        self.output_text = tk.Text(self.root, height=10, state="disabled")
        self.output_text.pack(pady=10, fill="x")

        self.input_entry = tk.Entry(self.root)
        self.input_entry.pack(pady=5, fill="x")
        self.input_entry.bind("<Return>", self.send_input)
        self.input_entry.config(state="disabled")

        self.awaiting_input = False
        self.current_ai_character = None

    def update_gui(self):
        for frame in [self.action_buttons_frame, self.item_buttons_frame, self.adjacent_rooms_frame, self.inventory_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        current_room = self.player.current_room
        self.location_label.config(text=current_room.name)
        self.location_desc.config(text=current_room.description)

        actions_dict = current_room.get_actions()
        actions = set(actions_dict.keys()) - {"go"}
        items = set(item.name for sublist in actions_dict.values() for item in sublist) - self.player.inv_items.keys() - current_room.get_rooms().keys()

        if self.selected_action:
            items = set(item.name for item in actions_dict[self.selected_action])
        if self.selected_item:
            actions = {action for action, objs in actions_dict.items() if any(obj.name == self.selected_item for obj in objs)}

        for action in actions:
            btn = tk.Button(self.action_buttons_frame, text=action.capitalize(),
                            command=lambda a=action: self.select_action(a))
            btn.pack(side="left", padx=5)

        for item_name in items:
            btn = tk.Button(self.item_buttons_frame, text=item_name,
                            command=lambda i=item_name: self.select_item(i))
            btn.pack(side="left", padx=5)

        for room_name, room in current_room.get_rooms().items():
            btn = tk.Button(self.adjacent_rooms_frame, text=room_name,
                            command=lambda r=room: self.move_to_room(r))
            btn.pack(side="left", padx=5)

        for inv_item in self.player.inv_items.values():
            lbl = tk.Button(self.inventory_frame, text=inv_item.name,
                            command=lambda i=inv_item: self.select_item(i.name))
            lbl.pack(side="left", padx=5)

    def select_action(self, action):
        self.selected_action = None if self.selected_action == action else action
        if self.selected_action and self.selected_item:
            self.execute_selected()
        else:
            self.update_gui()

    def select_item(self, item):
        self.selected_item = None if self.selected_item == item else item
        if self.selected_action and self.selected_item:
            self.execute_selected()
        else:
            self.update_gui()

    def execute_selected(self):
        action = self.selected_action
        item_name = self.selected_item
        item = next((obj for obj in self.player.current_room.get_actions()[action] if obj.name == item_name), None)
        if isinstance(item, AICharacter) and action.lower() == "talk":
            self.start_talk_ai(item)
        else:
            item.do(action)
        self.selected_action = None
        self.selected_item = None
        self.update_gui()

    def move_to_room(self, room):
        if isinstance(room, Door):
            if room.locked:
                messagebox.showinfo("Locked Door", "The door is locked.")
                return
            else:
                linked = list(room.linked.values())
                if linked[0] == self.player.current_room:
                    room = linked[1]
                else:
                    room = linked[0]
        self.end_talk_ai()
        room.go()
        self.update_gui()

    def start_talk_ai(self, ai_character):
        self.current_ai_character = ai_character
        self.input_entry.config(state="normal")
        self.input_entry.delete(0, "end")
        self.input_entry.focus()
        self.awaiting_input = True
        print(f"You are now talking to {ai_character.name}. Type your message and press Enter.")

    def end_talk_ai(self):
        self.awaiting_input = False
        self.input_entry.config(state="disabled")
        self.current_ai_character = None

    def send_input(self, event):
        if self.awaiting_input:
            user_input = self.input_entry.get()
            self.input_entry.delete(0, "end")
            print(f"You said: {user_input}")
            threading.Thread(target=self.current_ai_character.talk, args=(user_input,), kwargs={'once': True}, daemon=True).start()

    def reset_game(self):
        self.game.do_reset()
        self.update_gui()

    def redirect_stdout(self):
        sys.stdout = type('Redirector', (), {'write': lambda s, x: (self.output_text.config(state="normal"), self.output_text.insert("end", x), self.output_text.see("end"), self.output_text.config(state="disabled")), 'flush': lambda s: None})()

if __name__ == '__main__':
    root = tk.Tk()
    player = Character(lookable=False, health=3)
    Entity.set_player(player)
    adventure_game = Adventure(player)
    gui = AdventureGUI(root, adventure_game)
    root.mainloop()