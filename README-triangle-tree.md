# Triangle Tree Builder: `triangle_tree.py`

Interactive CLI for building trees of G/S/A triangles, the unit from
`triangle tree.png`:

```text
        G           G = Goal
       / \          S = Sensor
      S---A         A = Actuator
```

Each triangle also holds three behaviors: **control**, **plan** and
**navigate**. Triangles compose into a tree; every triangle fans out to
**at most two** child triangles.

## Starting

```bash
python triangle_tree.py
```

The program first asks for the **project name**, which becomes the tree's
name, the root triangle's name, and the save file (`<project>.json`). You
can also pass it directly:

```bash
python triangle_tree.py mason
```

## Example session

```text
project name (= tree name): mason
new tree 'mason' (root triangle: 'mason')

mason> add mason left
added 'left' under 'mason'
mason> add mason right
added 'right' under 'mason'
mason> add right lower
added 'lower' under 'right'
mason> set mason goal build wall
mason.goal = 'build wall'
mason> show
tree 'mason'
/\ mason  [1/6 fields]  G:build wall
|-- /\ left  [0/6 fields]
`-- /\ right  [0/6 fields]
    `-- /\ lower  [0/6 fields]
mason> quit
saved mason.json
```

## Commands

| Command | Effect |
|---|---|
| `add <parent> <name>` | add a child triangle under `<parent>` (max 2) |
| `set <name> <field> <text>` | fill a field: `goal` `sensor` `actuator` `control` `plan` `navigate` |
| `info <name>` | show all fields of one triangle |
| `show` | draw the tree as ASCII art |
| `remove <name>` | remove a triangle and its subtree (root is protected) |
| `rename <old> <new>` | rename a triangle (renaming the root renames the project and save file) |
| `save` | write `<project>.json` |
| `quit` | save and exit |

## Design points

- **Each triangle holds six fields**: the three corners (`goal`, `sensor`,
  `actuator`) and the three behaviors (`control`, `plan`, `navigate`).
- **Max fan-out of two is enforced** — a third `add` under the same parent
  is refused with a message naming the two existing children.
- **Triangle names must be unique** in the tree, so commands can address
  any triangle directly without paths.
- **The tree persists as `<project>.json`** (nested dicts mirroring the
  tree) and reloads automatically when the program is started with the
  same project name. Ctrl+C also saves before exiting, so a tree cannot
  be lost by accident.
- The JSON format is deliberately simple, so a later step — feeding the
  tree into the quark/triangle runtime, or drawing real triangles in an
  HTML view like `mason_builder.html` — can read it directly.
