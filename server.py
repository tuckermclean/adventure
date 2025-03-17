import sys
import io
import queue
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from adventure import Adventure
from characters import Character

app = Flask(__name__, static_folder='static')
CORS(app)

player = Character(lookable=False)
game = Adventure(player)

# Queue for handling input requests from AI characters
input_queue = queue.Queue()
waiting_for_input = False  # Track whether input() is waiting

def capture_output(func, *args, **kwargs):
    """Capture the stdout output of a function and return it as a string."""
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    return buffer.getvalue().strip()

# Override input() to wait for user input from the frontend
def custom_input(prompt=""):
    """Pauses execution and waits for input from the frontend."""
    global waiting_for_input
    print(prompt)  # Send prompt message
    waiting_for_input = True  # Mark that we are waiting for input
    return input_queue.get()  # Wait until the frontend provides input

# Redirect Python's built-in input() function
__builtins__.input = custom_input

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/command', methods=['POST'])
def process_command():
    """Handles user input and returns game output."""
    global waiting_for_input

    if waiting_for_input:
        return jsonify({"response": "Waiting for input..."})

    data = request.json
    command = data.get("command", "").strip()

    if not command:
        return jsonify({"response": "Please enter a command."})

    # Capture printed output (since the game relies on print())
    output = capture_output(game.onecmd, command)

    # If input() was triggered, notify the frontend
    if waiting_for_input:
        return jsonify({"response": output, "awaiting_input": True})
    
    return jsonify({"response": output})

@app.route('/submit_input', methods=['POST'])
def submit_input():
    """Receives user input from the frontend and continues execution."""
    global waiting_for_input

    data = request.json
    user_input = data.get("user_input", "").strip()

    if not user_input:
        return jsonify({"response": "No input received."})

    # Send user input to the waiting input() function
    input_queue.put(user_input)
    waiting_for_input = False  # Reset waiting flag

    # Process any pending output after receiving user input
    output = capture_output(lambda: None)  # Just to flush any output
    return jsonify({"response": output if output else "Processing complete."})

@app.route('/start', methods=['GET'])
def start_game():
    """Starts a new game session."""
    output = capture_output(game.preloop)
    return jsonify({"response": output})

if __name__ == '__main__':
    app.run(debug=True)
