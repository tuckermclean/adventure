from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from characters import Character, AICharacter
from entities import Entity, Room, HiddenDoor
from items import Weapon
from adventure import Adventure
import sys
import io

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)  # Enable CORS for all routes

app.secret_key = "supersecretkey"  # Replace with a secure key

# Initialize the game
player = Character(lookable=False, health=3)
Entity.set_player(player)
adventure_game = Adventure(player)
adventure_game.current_room_intro = lambda: None  # Disable intro for the server
# Global log buffer
log_buffer = []

class StdoutBuffer(io.StringIO):
    """ Redirects stdout to capture printed messages in a buffer. """
    def write(self, message):
        super().write(message)
        log_buffer.append(message)  # Store log messages in the global buffer

    def flush(self):
        pass

sys.stdout = StdoutBuffer()  # Redirect stdout to custom buffer

def get_game_state():
    """Fetches the current game state for the player."""
    current_room = Entity.player.current_room
    actions_dict = current_room.get_actions()

    # Create mappings of valid actions per item and valid items per action
    item_to_actions = {}
    action_to_items = {}
    inventory_items = {
        item_name: [] for item_name, item in Entity.player.inv_items.items()
    }

    for action, objects in actions_dict.items():
        if action == "go":
            continue  # Ignore movement actions
        
        for obj in objects:
            item_name = obj.name

            if item_name not in item_to_actions:
                item_to_actions[item_name] = []
            if item_name not in inventory_items:
                item_to_actions[item_name].append(action)
            else:
                inventory_items[item_name].append(action)
                del item_to_actions[item_name]

            if action not in action_to_items:
                action_to_items[action] = []
            action_to_items[action].append(item_name)

    adjacent_rooms = {
        room_name: room.name for room_name, room in current_room.get_rooms().items()
        if not (isinstance(room, HiddenDoor) and not room.condition())
    }

    return {
        "location": current_room.name,
        "description": current_room.description,
        "actions": action_to_items,  # Maps actions to valid items
        "items": item_to_actions,  # Maps items to valid actions
        "inventory": inventory_items,
        "adjacent_rooms": adjacent_rooms,
        "money": round(Entity.player.money, 2),
    }

@app.route('/')
def serve_index():
    """Serve the main index.html file."""
    return send_from_directory('static', 'index.html')

@app.route('/images/<path:filename>')
def serve_images(filename):
    """Serve images from the images directory."""
    return send_from_directory('images', filename)

@app.route('/state', methods=['GET'])
def game_state():
    """API to get the current game state."""
    return jsonify(get_game_state())

@app.route('/action', methods=['POST'])
def perform_action():
    """API to perform an action in the game."""
    data = request.json
    action = data.get("action")
    item_name = data.get("item")

    if not action:
        return jsonify({"error": "Action is required"}), 400

    current_room = Entity.player.current_room
    actions_dict = current_room.get_actions()

    if action not in actions_dict:
        return jsonify({"error": f"Invalid action: {action}"}), 400

    item = next((obj for obj in actions_dict[action] if obj.name == item_name), None)

    if isinstance(item, AICharacter) and action.lower() == "talk":
        request.talking_to = item.name
        return jsonify({"message": f"You are now talking to {item.name}.", "talking": True})

    elif isinstance(item, Weapon) and action.lower() == "use":
        return jsonify({"message": "Choose a target.", "targets": [e.name for e in current_room.get_items().values() if isinstance(e, Character) and e != Entity.player]})

    elif action.lower() == "look":
        print(item)
        return jsonify({"message": str(item)})

    elif action.lower() == "take":
        item.take(look=False)
        print(f"You took {item.name}.")
        return jsonify({"message": f"You took {item.name}."})

    else:
        item.do(action)
        return jsonify({"message": f"Performed {action} on {item_name}."})

@app.route('/move', methods=['POST'])
def move_to_room():
    """API to move to a different room."""
    data = request.json
    room_name = data.get("room")

    if not room_name:
        return jsonify({"error": "Room name is required"}), 400

    current_room = Entity.player.current_room.get_rooms().get(room_name)

    if not current_room:
        return jsonify({"error": f"No such room: {room_name}"}), 400

    current_room.go()
    return jsonify({"message": f"Moved to {room_name}.", "new_state": get_game_state()})

@app.route('/talk', methods=['POST'])
def talk_to_character():
    """API to talk to AI characters."""
    data = request.json
    message = data.get("message")
    character_name = data.get("talking_to", None)

    if not character_name:
        return jsonify({"error": "No conversation is in progress."}), 400

    ai_character = next((char for char in Character.get_all().values() if char.name == character_name), None)

    if not ai_character:
        return jsonify({"error": "Character not found"}), 404

    response = ai_character.talk(message, once=True)
    return jsonify({"response": response})

@app.route('/end_talk', methods=['POST'])
def end_talk():
    """API to end a conversation."""
    if hasattr(request, "talking_to"):
        del request.talking_to
    return jsonify({"message": "Conversation ended."})

@app.route('/logs', methods=['GET'])
def get_logs():
    """API to retrieve stdout logs."""
    global log_buffer
    logs = log_buffer[:]  # Copy the buffer
    log_buffer = []  # Clear the buffer after sending logs
    return jsonify({"logs": logs})

if __name__ == '__main__':
    app.run(debug=True)
