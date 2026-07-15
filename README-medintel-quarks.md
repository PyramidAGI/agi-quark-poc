# medintel_quarks.json — a triangle tree written in quark vocabulary

`medintel_quarks.json` is the quark-only version of `medintel.json`: the same
8-triangle tree (same structure, same node names), but every triangle field —
goal, sensor, actuator, control, plan, navigate — is composed **only** of quark
words from `numbered quarks.csv` (39 quarks). Every word in every field is
verified to appear in the quark list, and the file is valid JSON, viewable in
`triangle_viewer.html`.

## The domain

The tree describes an AI system that answers analyst queries about sales
reports of a company selling advanced medical machines, finding patterns in
product use and maintenance needs. See `medintel.json` for the full-prose
version of the same tree.

## How the prose translates into quark sequences

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

## Patterns in the quark usage

Some quarks got natural reuse across levels:

- `val` + `fix` appears in every control field — all controls are
  validate-and-repair.
- `pattern` climbs from leaf actuators into parent sensors, mirroring the
  aggregation flow of the original tree: leaf outputs become the parent's
  sensor input.
