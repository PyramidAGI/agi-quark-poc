# AGI Quark POC

This is a first proof-of-concept for the harness:

```text
LOG -> GROUNDING -> QUARKS -> TRIANGLES -> ACTIONS -> GOAL
```

## Files

- `poc_runner.py` — the Python CLI runtime.
- `log.csv` — triangle rules, goals, action effects, and grounding rules.
- `combinations.csv` — copied from the uploaded file; maps ordinary words to quarks.
- `mason-robot.csv` — a standalone triangle for a mason robot that builds a wall.
- `mason_builder.html` — browser simulation that runs the mason triangle (see below).
- `README-quark-turing.md` — design notes: a Turing machine over the quarks, why the current pipeline is not Turing complete, and three use cases for a quark tape.
- `triangle_tree.py` — interactive builder for trees of G/S/A triangles (max 2 children each); see `README-triangle-tree.md`.
- `triangle_viewer.html` — generic browser viewer for triangle tree JSON files: enter a tree name (or pick a file) and it draws the tree as SVG triangles; click a triangle to inspect its fields.

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

## Log record format

Every record in `log.csv` (and the triangle CSVs) has eight fields:

```text
natural language sentence ; e0 ; e1 ; e2 ; e3 ; e4 ; e5 ; e6
```

| field | name | meaning | example (triangle row) | example (grounding row) |
|---|---|---|---|---|
| — | sentence | natural language description | `natural surface detected` | `battery running low` |
| e0 | role | `q`, `a`, `c` or `i` | `a` | `i` |
| e1 | summary | row type / operator | `stat`, `mode`, `activity` | `lt`, `gt`, `eq` |
| e2 | concept1 | first concept | `robot001` | sensor name `battery_%` |
| e3 | concept2 | second concept | `tree001` | unit `%` |
| e4 | extra | quark, action, or `goal` cluster | `nature` | quark `stat low` |
| e5 | val | current/default reading — the environment speaking first | `30` | `75` |
| e6 | threshold | firing cutoff (grounding rules); acts as rule salience in stat rows | `40` | `30` |

Related records form a cluster, wrapped in `;;;;;;;;` separator rows. Only the first
record of a cluster carries the natural language sentence; the records that follow it
leave the sentence empty (e.g. an `a;stat` row has the sentence, its paired `c;mode`
row starts with `;c;mode;...`).

## How the POC uses the log

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

## Mason robot: `mason-robot.csv` + `mason_builder.html`

`mason_builder.html` is a self-contained browser simulation that runs the mason triangle from `mason-robot.csv`. Just double-click the file to watch a mason robot lay 30 bricks (5 courses × 6) and reach `goal support+shield` at around tick 49.

It mirrors the same pipeline as `poc_runner.py` (`LOG -> GROUNDING -> QUARKS -> TRIANGLES -> ACTIONS -> GOAL`):

- **The CSV is the program.** On load it fetches `mason-robot.csv` (falling back to an embedded copy when opened via `file://`, where browsers block fetch) and parses the triangle's stat→mode pairs, the `c;effect` rows, the grounding rules, and the goal cluster. The left panel shows all three rule cards, and rows flash amber as they fire.
- **Each tick**, simulated sensors (`course_fill_ratio`, `brick_offset_mm`, `mortar_moisture_%`, `wall_tilt_deg`, `wall_height_ratio`) run through the grounding rules to produce quarks; the matching triangle rule with the highest salience picks the mode; the mode animates on the SVG stage (bricks fly in, get tapped level, the wall skews when tilting and snaps plumb on `align_course`, the robot climbs scaffolding each course) and its `c;effect` rows emit quarks into the `seen` set — the same subset test as the Python runner then checks the goal.
- The right panel is a live event log, and the bottom bar shows sensor chips, the accumulating quark set (goal quarks light up green), plus run/pause, reset, and speed controls.

Two conventions in `mason-robot.csv` make it a runnable spec:

- **Every goal quark needs a producer.** The goal is `support+shield`: `support` is emitted by the `align_course` effect, and `shield` is grounded by `wall_height_ratio > 0.9`. A goal quark that no grounding rule or effect can produce makes the goal unreachable.
- **Stat-row activation numbers encode mode priority.** When several quarks fire in the same tick, the rule with the highest second activation value wins: `force` 60 > `stat rough` 55 > `stat dry` 50 > `pattern` 45 > `stat empty` 40. So the robot fixes a leaning wall or a crooked brick before laying the next one.
