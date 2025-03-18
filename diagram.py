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

# Generate and save the diagram
dot.render('adventure_world_diagram', view=True)
