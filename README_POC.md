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
