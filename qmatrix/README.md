# Q-matrix v0.1

`qmatrix_timss_v01.csv` codes every TIMSS 2019 and 2023 grade-8 Algebra item, and every
Number item tied to an algebra-readiness skill, to the 12 skills in `attributes.csv`. It was
drafted item by item from the IEA item-information files (topic area, cognitive area, item
type and the item's short label), then ruled on item by item by the author (2026-10-07).

| | TIMSS 2023 | TIMSS 2019 |
|---|---|---|
| items coded | 112 | 112 |
| shared trend items | 64 | 64 |
| items excluded (whole-number, primes, puzzles; see `excluded_items_v01.csv`) | 17 across both cycles | |
| confidence H / M / L | 124 / 31 / 9 across the 164 unique items | |

Items per skill (single-skill items in brackets):

| skill | 2023 | 2019 |
|---|---|---|
| A01 Rational-number operations | 32 (26) | 30 (24) |
| A02 Proportional reasoning | 30 (19) | 24 (20) |
| A03 Exponents and roots | 4 (2) | 6 (2) |
| A04 Evaluating expressions | 14 (5) | 11 (5) |
| A05 Equivalent expressions | 9 (5) | 13 (7) |
| A06 Symbolizing situations | 22 (3) | 22 (3) |
| A07 Linear equations and inequalities | 14 (3) | 11 (3) |
| A08 Systems of linear equations | 3 (1) | 3 (2) |
| **A09 Factoring and polynomial products** | **1 (0)** | **3 (0)** |
| A10 Patterns and generalization | 8 (4) | 9 (5) |
| A11 Functions and representations | 10 (1) | 7 (0) |
| A12 Linear functions | 6 (2) | 11 (5) |

## Findings

1. **Factoring cannot be measured from TIMSS grade 8.** One 2023 item and three 2019 items
   touch it, never on their own. The TIMSS fits fold A09 into A05 (`--merge A09:A05`);
   A09 stays in the dictionary for districts' own high-school tests, where it matters most.
2. **Systems of equations (A08) rest on three items per cycle.** Expect wide uncertainty; consider
   merging into A07 for TIMSS if classification accuracy is poor.
3. **A06 and A11 have few single-skill items** (symbolizing nearly always co-occurs with
   solving or functions). They are identified through combinations; check that their
   classification accuracy is acceptable before reporting them separately.
4. **Nine low-confidence items (L)** have labels too short to judge; they need a look at the
   item itself (IEA restricted-use item materials).

## Revising

The review sheet that pairs each row with IEA's item label stays on the author's computer
(IEA terms). Changes after v0.1 are logged in `CHANGELOG.md` with their reason; empirical
evidence from `qmatrix_validation.csv` (GDI/PVAF) after the US TIMSS fits will be the first
input to v0.2. The fit script refuses a Q-matrix with any row not marked `ok`.

Item labels and item text are IEA material and are not included in this public file.
