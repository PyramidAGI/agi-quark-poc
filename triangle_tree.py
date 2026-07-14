"""Interactive builder for trees of G/S/A triangles.

A triangle is the unit from `triangle tree.png`:

        G           G = Goal
       / \          S = Sensor
      S---A         A = Actuator

Each triangle also holds three behaviors: control, plan and navigate.
Triangles compose into a tree; every triangle fans out to AT MOST TWO
child triangles.

On start the program asks for a project name - that is also the tree's
name, the root triangle's name, and the save file (<project>.json).

Commands (inside the program):
    add <parent> <name>      add a child triangle under <parent> (max 2)
    set <name> <field> <text>   field: goal sensor actuator control plan navigate
    info <name>              show all fields of one triangle
    show                     draw the tree
    remove <name>            remove a triangle and its subtree (not the root)
    rename <old> <new>       rename a triangle
    save                     write <project>.json
    quit                     save and exit
"""

import json
import sys
from pathlib import Path

FIELDS = ("goal", "sensor", "actuator", "control", "plan", "navigate")
MAX_CHILDREN = 2


class Triangle:
    def __init__(self, name):
        self.name = name
        self.fields = {f: "" for f in FIELDS}
        self.children = []          # 0..MAX_CHILDREN Triangles

    def to_dict(self):
        return {"name": self.name, **self.fields,
                "children": [c.to_dict() for c in self.children]}

    @classmethod
    def from_dict(cls, d):
        t = cls(d["name"])
        for f in FIELDS:
            t.fields[f] = d.get(f, "")
        t.children = [cls.from_dict(c) for c in d.get("children", [])]
        return t


class Tree:
    def __init__(self, project):
        self.project = project
        self.path = Path(f"{project}.json")
        if self.path.exists():
            self.root = Triangle.from_dict(json.loads(self.path.read_text()))
            print(f"loaded existing tree from {self.path}")
        else:
            self.root = Triangle(project)
            print(f"new tree '{project}' (root triangle: '{project}')")

    # ---------------------------------------------------------- lookups

    def walk(self, node=None):
        node = node or self.root
        yield node
        for c in node.children:
            yield from self.walk(c)

    def find(self, name):
        for t in self.walk():
            if t.name == name:
                return t
        return None

    def parent_of(self, name):
        for t in self.walk():
            for c in t.children:
                if c.name == name:
                    return t
        return None

    # ---------------------------------------------------------- commands

    def add(self, parent_name, name):
        parent = self.find(parent_name)
        if parent is None:
            return f"no triangle named '{parent_name}'"
        if len(parent.children) >= MAX_CHILDREN:
            return (f"'{parent_name}' already fans out to {MAX_CHILDREN} "
                    f"triangles ({', '.join(c.name for c in parent.children)})")
        if self.find(name):
            return f"a triangle named '{name}' already exists"
        parent.children.append(Triangle(name))
        return f"added '{name}' under '{parent_name}'"

    def set(self, name, field, text):
        t = self.find(name)
        if t is None:
            return f"no triangle named '{name}'"
        if field not in FIELDS:
            return f"unknown field '{field}' (use: {' '.join(FIELDS)})"
        t.fields[field] = text
        return f"{name}.{field} = {text!r}"

    def remove(self, name):
        if name == self.root.name:
            return "cannot remove the root triangle"
        parent = self.parent_of(name)
        if parent is None:
            return f"no triangle named '{name}'"
        parent.children = [c for c in parent.children if c.name != name]
        return f"removed '{name}' and its subtree"

    def rename(self, old, new):
        t = self.find(old)
        if t is None:
            return f"no triangle named '{old}'"
        if self.find(new):
            return f"a triangle named '{new}' already exists"
        t.name = new
        if t is self.root:
            self.project = new
            self.path = Path(f"{new}.json")
        return f"renamed '{old}' to '{new}'"

    def info(self, name):
        t = self.find(name)
        if t is None:
            return f"no triangle named '{name}'"
        parent = self.parent_of(name)
        lines = [f"triangle '{t.name}'"
                 + (f"  (child of '{parent.name}')" if parent else "  (root)")]
        for f in FIELDS:
            lines.append(f"  {f:<9}: {t.fields[f] or '-'}")
        kids = ", ".join(c.name for c in t.children) or "-"
        lines.append(f"  children : {kids}  ({len(t.children)}/{MAX_CHILDREN})")
        return "\n".join(lines)

    def show(self):
        lines = [f"tree '{self.project}'"]

        def draw(node, prefix, tail):
            branch = "" if prefix == "" and tail else ("`-- " if tail else "|-- ")
            filled = sum(1 for f in FIELDS if node.fields[f])
            goal = f"  G:{node.fields['goal']}" if node.fields["goal"] else ""
            lines.append(f"{prefix}{branch}/\\ {node.name}"
                         f"  [{filled}/{len(FIELDS)} fields]{goal}")
            ext = "" if prefix == "" and tail else ("    " if tail else "|   ")
            for i, c in enumerate(node.children):
                draw(c, prefix + ext, i == len(node.children) - 1)

        draw(self.root, "", True)
        return "\n".join(lines)

    def save(self):
        self.path.write_text(json.dumps(self.root.to_dict(), indent=2))
        return f"saved {self.path}"


HELP = __doc__[__doc__.index("Commands"):]


def main():
    print("Triangle tree builder - trees of G/S/A triangles (max 2 children each)")
    project = " ".join(sys.argv[1:]) or ""
    while not project.strip():
        try:
            project = input("project name (= tree name): ").strip()
        except (KeyboardInterrupt, EOFError):
            return
    tree = Tree(project)
    print("type 'help' for commands\n")

    while True:
        try:
            line = input(f"{tree.project}> ").strip()
        except (KeyboardInterrupt, EOFError):
            print(tree.save())
            return
        if not line:
            continue
        cmd, *rest = line.split(maxsplit=1)
        arg = rest[0] if rest else ""
        try:
            if cmd == "help":
                print(HELP)
            elif cmd == "add":
                parent, name = arg.split()
                print(tree.add(parent, name))
            elif cmd == "set":
                name, field, text = arg.split(maxsplit=2)
                print(tree.set(name, field, text))
            elif cmd == "info":
                print(tree.info(arg.strip()))
            elif cmd == "show":
                print(tree.show())
            elif cmd == "remove":
                print(tree.remove(arg.strip()))
            elif cmd == "rename":
                old, new = arg.split()
                print(tree.rename(old, new))
            elif cmd == "save":
                print(tree.save())
            elif cmd in ("quit", "exit"):
                print(tree.save())
                return
            else:
                print(f"unknown command '{cmd}' - type 'help'")
        except ValueError:
            print(f"bad arguments for '{cmd}' - type 'help'")


if __name__ == "__main__":
    main()
