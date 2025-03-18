import yaml
from graphviz import Digraph

# Load your world YAML data
with open('world.yaml', 'r', encoding='utf-8') as file:
    data = yaml.safe_load(file)

# Create directed graph
dot = Digraph(comment='Adventure World', format='png')
dot.attr(rankdir='LR')

# Add rooms as nodes
for room in data['rooms']:
    dot.node(room['name'], room['name'])

# Add links between rooms
for room in data['rooms']:
    for link in room.get('links', []):
        dot.edge(room['name'], link)

# Add doors as edges with special styling
for door in data.get('doors', []):
    dot.edge(door['room1'], door['room2'], label=f"Door: {door['name']}", style='dashed', color='red')

# Add items as subnodes
for room in data['rooms']:
    for item in room.get('items', []):
        dot.node(f"{room['name']}_{item['name']}", item['name'], shape='box')
        dot.edge(room['name'], f"{room['name']}_{item['name']}", style='dotted')
        # Add item actions as text labels
        if item['type'] in ['Item', 'Wearable', 'Eatable', 'Weapon', 'Money'] and item.get('takeable', True):
            dot.node(f"{room['name']}_{item['name']}_take", "take", shape='plaintext')
            dot.edge(f"{room['name']}_{item['name']}", f"{room['name']}_{item['name']}_take", style='dotted')
        if 'verb' in item:
            dot.node(f"{room['name']}_{item['name']}_{item['verb']}", item['verb'], shape='plaintext')
            dot.edge(f"{room['name']}_{item['name']}", f"{room['name']}_{item['name']}_{item['verb']}", style='dotted')
        else:
            if item['type'] in ['Useable', 'Computer', 'Phone', 'Weapon']:
                dot.node(f"{room['name']}_{item['name']}_use", "use", shape='plaintext')
                dot.edge(f"{room['name']}_{item['name']}", f"{room['name']}_{item['name']}_use", style='dotted')
            elif item['type'] == 'Wearable':
                dot.node(f"{room['name']}_{item['name']}_wear", "wear", shape='plaintext')
                dot.edge(f"{room['name']}_{item['name']}", f"{room['name']}_{item['name']}_wear", style='dotted')
            elif item['type'] == 'Eatable':
                dot.node(f"{room['name']}_{item['name']}_eat", "eat", shape='plaintext')
                dot.edge(f"{room['name']}_{item['name']}", f"{room['name']}_{item['name']}_eat", style='dotted')

# Add characters as subnodes
for character in data.get('characters', []):
    dot.node(f"{character['current_room']}_{character['name']}", character['name'], shape='ellipse', color='lightblue')
    dot.edge(character['current_room'], f"{character['current_room']}_{character['name']}", style='dotted')
    # Add item actions as text labels
    if 'verb' in character:
        dot.node(f"{character['current_room']}_{character['name']}_{character['verb']}", character['verb'], shape='plaintext')
        dot.edge(f"{character['current_room']}_{character['name']}", f"{character['current_room']}_{character['name']}_{character['verb']}", style='dotted')
    elif character['type'] == 'AICharacter':
        dot.node(f"{character['current_room']}_{character['name']}_talk", "talk", shape='plaintext')
        dot.edge(f"{character['current_room']}_{character['name']}", f"{character['current_room']}_{character['name']}_talk", style='dotted')


# Generate and save the diagram
dot.render('adventure_world_diagram', view=True)
