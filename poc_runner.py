#!/usr/bin/env python3
"""
poc_runner.py

A first proof-of-concept for the LOG -> GROUNDING -> QUARKS -> TRIANGLES -> ACTIONS loop.

Files:
  log.csv           semicolon records with triangles, goals, grounding rules, and effects
  combinations.csv  word -> quark mapping dictionary

Try:
  python poc_runner.py --demo
  python poc_runner.py

Interactive commands:
  observe stem robot grasper
  sensor battery_%=22
  tick
  quark nature support machine tool
  state
  help
  quit
"""

from __future__ import annotations

import argparse
import csv
import re
import shlex
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def clean(x: object) -> str:
    return str(x or "").strip()


def split_quarks(text: str) -> list[str]:
    """
    Splits "goal bond+support" or "stat full+bond" into quark names.
    Preserves quarks with spaces, such as "stat full".
    """
    text = clean(text)
    if text.lower().startswith("goal "):
        text = text[5:].strip()
    return [q.strip() for q in text.split("+") if q.strip()]


def slug(text: str) -> str:
    """A readable triangle key from a description."""
    text = clean(text)
    text = text.split("—")[0].strip()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return text or "triangle"


@dataclass
class GroundingRule:
    description: str
    op: str
    sensor: str
    unit: str
    quark: str
    value: float
    threshold: float

    def fires(self, reading: float) -> bool:
        if self.op == "lt":
            return reading < self.threshold
        if self.op == "gt":
            return reading > self.threshold
        if self.op == "eq":
            return reading == self.threshold
        raise ValueError(f"Unsupported grounding operator: {self.op!r}")


@dataclass
class Triangle:
    name: str
    description: str = ""
    rules: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    goal: set[str] = field(default_factory=set)


@dataclass
class LoadedSystem:
    triangles: dict[str, Triangle] = field(default_factory=dict)
    grounding_rules: list[GroundingRule] = field(default_factory=list)
    effects: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    combinations: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


class QuarkPOC:
    def __init__(self, loaded: LoadedSystem):
        self.loaded = loaded
        self.sensor_values: dict[str, float] = {}
        self.seen: dict[str, set[str]] = defaultdict(set)

    @classmethod
    def from_files(cls, log_path: str | Path, combinations_path: str | Path) -> "QuarkPOC":
        loaded = LoadedSystem()
        loaded.combinations = load_combinations(combinations_path)

        current_triangle: str | None = None
        pending_sensor_quark: str | None = None

        with open(log_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            for raw in reader:
                row = (raw + [""] * 8)[:8]
                desc, role, typ, e1, e2, rel, value, threshold = map(clean, row)
                role = role.lower()
                typ = typ.lower()

                if not any(row):
                    continue
                if is_separator(row) or desc.lower() in {"grounding rules", "action effects"}:
                    continue

                # Grounding rules: description;i;lt|gt;sensor;unit;quark;value;threshold
                if role == "i" and typ in {"lt", "gt", "eq"}:
                    loaded.grounding_rules.append(
                        GroundingRule(
                            description=desc,
                            op=typ,
                            sensor=e1,
                            unit=e2,
                            quark=rel,
                            value=to_float(value, 0.0),
                            threshold=to_float(threshold, 0.0),
                        )
                    )
                    continue

                # Optional POC extension:
                # description;c;effect;action;actor;quark(+quark);0;0
                if role == "c" and typ == "effect":
                    for q in split_quarks(rel):
                        loaded.effects[e1].add(q)
                    continue

                # Triangle header or goal line.
                if role == "c" and typ == "activity":
                    if rel.lower().startswith("goal "):
                        if current_triangle is None:
                            current_triangle = slug(desc or e1 or "triangle")
                            loaded.triangles.setdefault(current_triangle, Triangle(current_triangle, desc))
                        loaded.triangles[current_triangle].goal.update(split_quarks(rel))
                    else:
                        current_triangle = slug(desc)
                        loaded.triangles.setdefault(
                            current_triangle,
                            Triangle(name=current_triangle, description=desc),
                        )
                    pending_sensor_quark = None
                    continue

                # Sensor row. In this POC the relation field is the incoming quark.
                if role == "a" and typ in {"stat", "dyn", "loc", "rel"}:
                    pending_sensor_quark = rel
                    continue

                # Action row. Pairs with the preceding sensor row.
                if role == "c" and typ == "mode" and pending_sensor_quark and current_triangle:
                    tri = loaded.triangles.setdefault(
                        current_triangle,
                        Triangle(name=current_triangle, description=current_triangle),
                    )
                    tri.rules[pending_sensor_quark].append(rel)
                    pending_sensor_quark = None
                    continue

        return cls(loaded)

    def observe_words(self, words: Iterable[str]) -> set[str]:
        quarks: set[str] = set()
        unknown: list[str] = []

        for word in words:
            key = word.lower().strip(",.;:!?()[]{}")
            if not key:
                continue
            mapped = self.loaded.combinations.get(key)
            if mapped:
                quarks.update(mapped)
            else:
                unknown.append(word)

        if unknown:
            print("unknown words:", ", ".join(unknown))

        return self.route(quarks, source="observe")

    def tick(self) -> set[str]:
        quarks: set[str] = set()
        print("sensor readings:")
        for rule in self.loaded.grounding_rules:
            if rule.sensor not in self.sensor_values:
                continue
            reading = self.sensor_values[rule.sensor]
            if rule.fires(reading):
                quarks.add(rule.quark)
                print(f"  {rule.sensor}={reading:g} {rule.unit} -> {rule.quark}  ({rule.description})")
        if not quarks:
            print("  no grounding rule fired")
        return self.route(quarks, source="tick")

    def route(self, quarks: Iterable[str], source: str = "quark") -> set[str]:
        active = set(q for q in quarks if q)
        if not active:
            return set()

        print(f"active quarks from {source}: {sorted(active)}")

        # Fire rules. Effects may add more quarks, so continue until stable.
        queue = list(active)
        fired: set[tuple[str, str, str]] = set()
        all_quarks = set(active)

        while queue:
            q = queue.pop(0)

            for tri in self.loaded.triangles.values():
                self.seen[tri.name].add(q)

                for action in tri.rules.get(q, []):
                    key = (tri.name, q, action)
                    if key in fired:
                        continue
                    fired.add(key)
                    print(f"  [{tri.name}] {q} -> {action}")

                    for effect_q in sorted(self.loaded.effects.get(action, set())):
                        if effect_q not in all_quarks:
                            all_quarks.add(effect_q)
                            queue.append(effect_q)
                            print(f"    effect: {action} -> {effect_q}")

                self.check_goal(tri)

        return all_quarks

    def check_goal(self, tri: Triangle) -> None:
        if tri.goal and tri.goal.issubset(self.seen[tri.name]):
            print(f"  [{tri.name}] GOAL REACHED: {sorted(tri.goal)}")
            self.seen[tri.name].clear()

    def reset(self) -> None:
        self.seen.clear()

    def clear_sensors(self) -> None:
        self.sensor_values.clear()

    def print_state(self) -> None:
        print("\n--- sensors ---")
        if self.sensor_values:
            for k, v in sorted(self.sensor_values.items()):
                print(f"{k} = {v:g}")
        else:
            print("(none)")

        print("\n--- triangles ---")
        for tri in self.loaded.triangles.values():
            print(f"{tri.name}")
            print(f"  goal: {sorted(tri.goal) if tri.goal else '(none)'}")
            print(f"  seen: {sorted(self.seen[tri.name]) if self.seen[tri.name] else '(none)'}")
            for q, actions in sorted(tri.rules.items()):
                print(f"  {q} -> {', '.join(actions)}")
        print()

    def run_demo(self) -> None:
        print("\nDEMO 1 — natural anchor from combinations.csv")
        print("observe stem robot grasper")
        self.observe_words(["stem", "robot", "grasper"])

        print("\nDEMO 2 — battery grounding from sensor threshold")
        print("sensor battery_%=22; tick")
        self.sensor_values["battery_%"] = 22
        self.tick()

        print("\nobserve battery")
        self.observe_words(["battery"])

        print("\nsensor battery_%=90; tick")
        self.sensor_values["battery_%"] = 90
        self.tick()

        print("\nDEMO 3 — social room")
        print("(resetting seen quarks and sensors so this demo is isolated)")
        self.reset()
        self.clear_sensors()

        print("sensor voice_pitch_hz=300; tick")
        self.sensor_values["voice_pitch_hz"] = 300
        self.tick()

        print("\nmanual quark bond")
        self.route({"bond"}, source="manual")

    def repl(self) -> None:
        print("Quark POC runner. Type 'help' for commands.")
        while True:
            try:
                line = input("poc> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue

            parts = shlex.split(line)
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in {"quit", "exit"}:
                break
            if cmd == "help":
                print(HELP)
            elif cmd == "demo":
                self.run_demo()
            elif cmd == "state":
                self.print_state()
            elif cmd == "reset":
                self.reset()
                print("seen quarks reset")
            elif cmd == "clear":
                self.clear_sensors()
                print("sensor values cleared")
            elif cmd == "tick":
                self.tick()
            elif cmd == "observe":
                self.observe_words(args)
            elif cmd == "quark":
                self.route(args, source="manual")
            elif cmd == "sensor":
                for item in args:
                    self.set_sensor_from_assignment(item)
            elif "=" in line and len(parts) == 1:
                self.set_sensor_from_assignment(line)
            else:
                print("Unknown command. Try: help")

    def set_sensor_from_assignment(self, item: str) -> None:
        if "=" not in item:
            print(f"bad sensor assignment: {item!r}; expected sensor=value")
            return
        name, value = item.split("=", 1)
        try:
            self.sensor_values[name.strip()] = float(value)
        except ValueError:
            print(f"bad numeric value: {value!r}")
            return
        print(f"{name.strip()} = {float(value):g}")


HELP = """
Commands:
  observe stem robot grasper      map words through combinations.csv, then route quarks
  sensor battery_%=22             set a sensor value
  battery_%=22                    shorthand for sensor assignment
  tick                            evaluate sensor values through i;lt / i;gt grounding rules
  quark nature support machine    inject quarks directly
  demo                            run the built-in demo
  state                           show loaded triangles, goals, sensors, and seen quarks
  reset                           clear accumulated seen quarks
  clear                           clear sensor values
  quit                            exit
"""


def is_separator(row: list[str]) -> bool:
    return all(clean(x) == "" for x in row) or (clean(row[0]) == "" and all(clean(x) == "" for x in row[1:]))


def to_float(text: str, default: float) -> float:
    try:
        return float(text)
    except ValueError:
        return default


def load_combinations(path: str | Path) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if len(row) < 2:
                continue
            word = clean(row[0]).lower()
            quark = clean(row[1])
            if word and quark:
                mapping[word].add(quark)
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="LOG -> GROUNDING -> QUARKS -> TRIANGLES -> ACTIONS POC")
    parser.add_argument("--log", default="log.csv", help="Path to semicolon log file")
    parser.add_argument("--combinations", default="combinations.csv", help="Path to word->quark mapping")
    parser.add_argument("--demo", action="store_true", help="Run demo and exit")
    args = parser.parse_args()

    app = QuarkPOC.from_files(args.log, args.combinations)

    if args.demo:
        app.run_demo()
    else:
        app.repl()


if __name__ == "__main__":
    main()
