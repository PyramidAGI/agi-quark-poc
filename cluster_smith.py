#!/usr/bin/env python3
"""
cluster_smith.py

A little forge for triangle clusters. It connects the world model trees
(humanoid.json, plantworldmodel.json) with log.csv:

  python cluster_smith.py humanoid.json           show the tree, mark quarks already in log.csv
  python cluster_smith.py humanoid.json ears      forge a paste-ready log.csv cluster for a node
  python cluster_smith.py plantworldmodel.json --log log.csv

The forge follows the house recipe: sensor quarks become a;stat situations,
navigate/actuator/control words become c;mode responses, and the goal row
combines the node's key quarks. Edit the drafted sentences, then paste the
block into log.csv above the 'action effects' section.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in {"utf-8", "utf8"}:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUARK_FIELDS = ["goal", "sensor", "actuator", "control", "plan", "navigate"]
FIELD_TAGS = {"goal": "goal", "sensor": "sens", "actuator": "act",
              "control": "ctrl", "plan": "plan", "navigate": "nav"}


def tokenize(text: str) -> list[str]:
    """Split a quark field into quarks, keeping 'stat X' pairs together."""
    words = (text or "").split()
    out, i = [], 0
    while i < len(words):
        if words[i] == "stat" and i + 1 < len(words):
            out.append(f"stat {words[i + 1]}")
            i += 2
        else:
            out.append(words[i])
            i += 1
    return out


def log_quarks(log_path: Path) -> set[str]:
    """All quarks that already appear in log.csv stat, goal, and effect rows."""
    seen: set[str] = set()
    if not log_path.exists():
        return seen
    with open(log_path, newline="", encoding="utf-8-sig") as f:
        for raw in csv.reader(f, delimiter=";"):
            row = (raw + [""] * 8)[:8]
            role, typ, rel = row[1].strip().lower(), row[2].strip().lower(), row[5].strip()
            if role == "a" and typ == "stat":
                seen.add(rel)
            elif role == "c" and typ in {"activity", "effect"}:
                text = rel[5:] if rel.lower().startswith("goal ") else rel
                seen.update(q.strip() for q in text.split("+") if q.strip())
            elif role == "i" and typ in {"lt", "gt", "eq"}:
                seen.add(rel)
    return seen


def show_tree(node: dict, known: set[str], prefix: str = "", is_last: bool = True,
              is_root: bool = True, stats: list[int] | None = None) -> None:
    if stats is None:
        stats = [0, 0]  # [covered, total]

    badges = []
    for field in QUARK_FIELDS:
        quarks = tokenize(node.get(field, ""))
        if not quarks:
            continue
        marked = []
        for q in quarks:
            stats[1] += 1
            if q in known:
                stats[0] += 1
                marked.append(f"{q}*")
            else:
                marked.append(q)
        badges.append(f"{FIELD_TAGS[field]}[{' '.join(marked)}]")

    connector = "" if is_root else ("└─ " if is_last else "├─ ")
    line = f"{prefix}{connector}{node.get('name', '?')}"
    if badges:
        line += "  " + "  ".join(badges)
    print(line)

    children = node.get("children", [])
    child_prefix = prefix if is_root else prefix + ("   " if is_last else "│  ")
    for i, child in enumerate(children):
        show_tree(child, known, child_prefix, i == len(children) - 1, False, stats)

    if is_root:
        pct = 100 * stats[0] // stats[1] if stats[1] else 0
        print(f"\nquark coverage in log: {stats[0]}/{stats[1]} ({pct}%)   (* = already appears in log.csv)")


def find_node(node: dict, name: str) -> dict | None:
    if node.get("name", "").lower() == name.lower():
        return node
    for child in node.get("children", []):
        hit = find_node(child, name)
        if hit:
            return hit
    return None


def mode_name(quark_or_phrase: str) -> str:
    return quark_or_phrase.replace(" ", "_")


def forge(tree: dict, node: dict) -> None:
    root = tree.get("name", "agent")
    name = node["name"]
    stats = tokenize(node.get("sensor", ""))
    modes = [mode_name(m) for field in ("navigate", "actuator", "control")
             for m in [node.get(field, "").strip()] if m]
    goals = tokenize(node.get("goal", "")) or stats

    print(rf"""
        /\
       /  \
      / {name[:2]} \
     /______\
   {root} · {name}
""")
    if not stats:
        print(f"node '{name}' has no sensor quarks; forging from its other fields.\n")
        stats = goals

    lines = [f"{name} triangle — {node.get('goal') or 'elaborate ' + name};c;activity;{root};{name};;60;50;"]
    e5 = 30
    for i, quark in enumerate(stats):
        mode = modes[i % len(modes)] if modes else f"handle_{mode_name(quark)}"
        lines += [";;;;;;;;",
                  f"{name} reports {quark};a;stat;{root}001;{name}001;{quark};{e5};{e5 + 10};",
                  f";c;mode;{root}001;{name}001;{mode};{e5 + 5};{e5 + 15};"]
        e5 += 10
    lines += [";;;;;;;;",
              f"{name} goal reached;c;activity;{root};{name};goal {'+'.join(goals)};80;90;"]

    print("\n".join(lines))
    print(f"\nedit the sentences and the counterpart '{name}' (e3 is usually the thing "
          f"sensed, e.g. 'sound' rather than 'ears'), then paste above 'action effects' in log.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description="show quark coverage of a triangle tree, or forge a cluster draft")
    parser.add_argument("tree", help="world model json (e.g. humanoid.json)")
    parser.add_argument("node", nargs="?", help="node name to forge a cluster for")
    parser.add_argument("--log", default="log.csv", help="log file to check coverage against")
    args = parser.parse_args()

    tree = json.loads(Path(args.tree).read_text(encoding="utf-8-sig"))

    if args.node:
        node = find_node(tree, args.node)
        if node is None:
            sys.exit(f"no node named {args.node!r} in {args.tree}")
        forge(tree, node)
    else:
        show_tree(tree, log_quarks(Path(args.log)))


if __name__ == "__main__":
    main()
