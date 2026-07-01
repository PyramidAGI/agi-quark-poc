# AGI Quark POC

This is a first proof-of-concept for the harness:

```text
LOG -> GROUNDING -> QUARKS -> TRIANGLES -> ACTIONS -> GOAL
```

## Files

- `poc_runner.py` — the Python CLI runtime.
- `log.csv` — triangle rules, goals, action effects, and grounding rules.
- `combinations.csv` — copied from the uploaded file; maps ordinary words to quarks.

## Run the demo

```bash
python poc_runner.py --demo
```

## Run interactively

```bash
python poc_runner.py
```

Then try:

```text
observe stem robot grasper
sensor battery_%=22
tick
observe battery
sensor battery_%=90
tick
state
reset
clear
```

## How the POC uses the log

The runner parses records shaped as:

```text
description ; role ; type/operator ; e1 ; e2 ; relation/quark/action ; value ; threshold
```

The core patterns are:

```text
i;lt / i;gt       sensor value -> quark
a;stat + c;mode   quark -> action
c;activity goal   goal cluster
c;effect          action -> emitted quark
```

The `c;effect` rows are a small POC bridge so printed actions can create new quarks, for example:

```text
engage_anchor -> bond
```

That lets the demo reach the goal `bond+support` without real hardware.

## How goal matching works

Each `Triangle` has a `goal` field: a set of quark names parsed from its `c;activity` row where the relation starts with `goal `, e.g.

```text
anchor established, robot secured;c;activity;robot;tree;goal bond+support;80;90;
```

becomes `goal = {bond, support}`.

At runtime, `QuarkPOC` keeps `seen[triangle_name]`, a set that accumulates every quark that has ever passed through `route()`. Whenever a quark is processed, it's added to the `seen` set of **every** triangle (not just the one whose rule fired for it) before that triangle's own `quark -> action` rules are checked and any `c;effect` quarks are queued up.

After each quark is processed, `check_goal()` runs a plain subset test:

```python
if tri.goal and tri.goal.issubset(self.seen[tri.name]):
    print(f"  [{tri.name}] GOAL REACHED: {sorted(tri.goal)}")
    self.seen[tri.name].clear()
```

So a goal fires once every quark it names has shown up at some point since the last reset — order doesn't matter, and the quarks don't need to arrive in the same `tick`/`observe` call. Once satisfied, that triangle's `seen` set is cleared so the goal can fire again later.

Because `seen` is updated for all triangles on every quark, a quark produced while satisfying one triangle's rules can also silently count toward another triangle's goal, even if that triangle's own rules never matched it.
