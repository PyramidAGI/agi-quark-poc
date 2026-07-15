# medintel triangle trees written in quark vocabulary

The medintel triangle tree describes an AI system that answers analyst queries
about sales reports of a company selling advanced medical machines, finding
patterns in product use and maintenance needs. It exists in three versions,
all with the same 8-triangle structure and node names, viewable in
`triangle_viewer.html`:

- `medintel.json` — full-prose fields.
- `medintel_quarks.json` — every triangle field (goal, sensor, actuator,
  control, plan, navigate) composed **only** of quark words from
  `numbered quarks.csv` (39 quarks).
- `medintel_quarks2.json` — fields drawn from the combined 66-quark
  vocabulary of `numbered quarks.csv` **and** `complement quarks.csv`
  (two-word quarks like `stat broken` count as single tokens).

Both quark versions are verified: every field parses entirely into quarks
from their respective lists.

## medintel_quarks.json — how the prose translates into quark sequences

- **medintel** (root): goal `solve pattern problem`, plan
  `sequence data pattern solve`, navigate `channel group waitfor event` —
  "route between the groups and wait for events until the pattern problem is
  solved."
- **erp-connector**: sensor `transaction contract data` (invoices, service
  contracts), actuator `transport data container` (move rows into the store),
  control `stat val fix` (validate counts, repair partial pulls).
- **report-cleaner**: sensor `data conflict problem` (messy free text),
  control `conflict val fix` (quarantine contradictions), plan
  `expand data pattern group` (unfold notes into tagged patterns).
- **usage-patterns**: sensor `data activity time energy` (operating hours and
  intensity), actuator `group pattern stat` (usage clusters with statistics).
- **maintenance-forecast**: goal `waitfor event fix` — the whole "fix it
  before the failure event" idea in three quarks; actuator
  `event fix tool sequence` is the watchlist of upcoming service actions.
- **insight-delivery**: goal `reward organization` (business value delivered),
  navigate `sequence pref dominate` (order findings by preference/impact).

## medintel_quarks2.json — what the complement quarks add

The complement vocabulary makes the tree noticeably more expressive:

- **maintenance-forecast** is the big winner: goal
  `waitfor event fix machine stat broken` ("anticipate the machine-broken
  event and fix first"), sensor `data time force vitality stat hot` — machine
  health (`vitality`) and overheating (`stat hot`) as wear signals.
- **usage-patterns**: sensor gains `transducer` (the machines' own probes as
  data source), and the actuator `group pattern mode stat fast stat slow`
  names the two usage clusters directly — fast 24/7 hospitals vs. slow
  weekday clinics.
- `kinship` expresses "machine family" in the navigate fields of
  report-harvest, report-cleaner, usage-patterns and maintenance-forecast —
  drill down within families of related machines.
- `fork` captures dispatch: the root and query-engine navigate/plan fields
  use it for "branch the question to the right miner."
- **report-cleaner** senses `emo` (engineer frustration in free-text notes)
  and controls with `stat rough` (quarantine rough/unclean rows);
  **insight-delivery** also senses `emo` and controls with `stat clear` —
  only publish clear insights.
- `bond` in report-harvest expresses record linking — bind every report to
  its machine serial.

## Patterns in the quark usage

Some quarks got natural reuse across levels:

- `val` + `fix` appears in every control field — all controls are
  validate-and-repair.
- `pattern` climbs from leaf actuators into parent sensors, mirroring the
  aggregation flow of the original tree: leaf outputs become the parent's
  sensor input.
