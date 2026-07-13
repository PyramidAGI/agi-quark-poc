# A Turing Machine over Quarks

Design notes on making a Turing machine that operates on the 39 semantic
primitives in `numbered quarks.csv`, and what such a machine could be *for*.

## Is it possible?

Yes, in two different senses.

### Sense 1: a TM whose alphabet is the quarks — trivially possible

A Turing machine needs a finite tape alphabet, a finite set of states, a
head, and a transition table. The quarks are a numbered finite alphabet
(1–39), which is all a TM asks for. A machine whose tape cells each hold one
quark, with rules like

```text
state=q2, read=radiation(5)  ->  write=shield(2), move=R, next=q3
```

is standard TM territory. The transition table can live in a CSV in the
existing log format, keeping the project's "the CSV is the program"
convention. Some quarks map naturally onto the TM machinery itself, making
the encoding self-describing:

| TM concept      | Quark            |
|-----------------|------------------|
| tape            | `sequence` (32)  |
| head position   | `loc` (9)        |
| one step        | `event` (25)     |
| write           | `fix` (14)       |
| machine state   | `stat` (36)      |
| halt condition  | `waitfor` (24)   |

### Sense 2: the existing quark pipeline is NOT Turing complete — but it is one change away

The current runner (grounding -> triangles -> `seen` sets -> subset goal
test -> effects) is bounded: `seen` is a set over 39 quark names, so each
triangle has at most 2^39 states, and quarks only *accumulate* until a goal
clears the set. Bounded state + monotone accumulation = a finite state
machine, and FSMs cannot do unbounded computation.

Turing completeness needs exactly one added ingredient: **unbounded
memory**. Two natural options:

1. **A quark tape** — one ordered, unbounded sequence of quark numbers plus
   a head index; triangle rules read the quark under the head, write one
   back, and move the head.
2. **Quark counters** — quarks get unbounded *multiplicity* (a count, not
   set membership) and effects can both emit and *consume* them. Two
   counters with increment / decrement / test-for-zero form a Minsky
   machine, which is Turing complete. The vocabulary cooperates:
   `increase` (26) and `contract` (37) are the two operations, `stat` the
   zero test. The consume operation matters as much as the counting: as
   long as quarks can only ever be added, the system stays monotone and
   decidable no matter how you count them.

Option 1 stays legible as a demo — the tape prints as a row of quark names
and you can watch the machine rewrite meaning — so it is the preferred
route.

## What could the quark tape represent? Three use cases

A tape of quarks is "an ordered, unbounded sequence of semantic
primitives," so the question becomes: *what in this domain is naturally a
sequence that gets read and rewritten?*

### 1. Physical space as the tape — the mason robot IS a Turing machine

Each tape cell is one brick position along a course, holding a quark
describing its state; the robot is the head:

```text
tape:  empty  empty  problem  support  support   (one wall course)
head:  the robot's position on the course = loc
step:  read `empty`   -> write `support` (lay brick), move R
       read `problem` -> write `fix`, stay (re-level the brick)
halt:  whole tape reads `support` -> emit `shield`, course done
```

The head-position quark `loc` is literally the robot's location, and
writing a symbol is literally an actuator command. Multi-course logic
(climb the scaffolding when a course is complete) is exactly a TM changing
state at an end-marker. This gives `mason_builder.html` a formal spine —
the wall is the memory, which is an honest claim about construction
robots: their working memory largely *is* the partially built structure.

### 2. Plan compilation — rewriting a goal into an action sequence

The tape starts as a *description* of a situation in quarks and the machine
rewrites it, pass by pass, into an executable sequence:

```text
start:  problem  food  loc            ("need food at some location")
pass 1: solve    food  loc            (commit to solving)
pass 2: transport  loc  food  own     (plan: go there, acquire)
halt:   tape is all action-quarks -> feed it to the triangle runtime
```

The TM sits *upstream* of the existing pipeline: triangles are reactive
(sensor -> quark -> action in one step), while the tape machine is
deliberative — it can transform a representation an unbounded number of
times *before* anything acts. That is the classic reactive/deliberative
split in agent architectures: the tape is the agent's working memory, and
thinking is rewriting.

### 3. Log diagnosis — pattern -> solve over an event stream

The tape is a sensor-event history in quarks (which the grounding rules
already produce); the machine scans for patterns and rewrites them into
diagnoses:

```text
tape:  radiation increase increase shield conflict ...
rule:  see `radiation increase increase` -> rewrite to `problem`
rule:  see `problem shield`              -> rewrite to `solve fix`
```

This uses `pattern` (34), `problem` (33), `solve` (35) exactly as named.
Unboundedness is real here — logs grow without limit, and some patterns
(e.g. "every `expand` is eventually followed by a matching `contract`")
are provably beyond a finite-state matcher, which is precisely the gap the
tape closes.

## Recommendation

Build **use case 1** first: it is the only one where every TM ingredient
has a physical referent (tape = wall, head = robot, write = lay brick), it
plugs into the existing mason demo, and it makes the Turing-completeness
claim demonstrable rather than rhetorical. Use case 2 is the more profound
direction for the AGI story, but it needs a rewrite-rule vocabulary to be
designed; it is a natural second step once the tape machinery exists.
