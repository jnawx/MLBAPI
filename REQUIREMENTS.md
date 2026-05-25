# MLB Database & API — Requirements

## Status: Discovery / Requirements Gathering

---

## Core Vision
A personal MLB database and API capable of handling **moderately complex statistical queries** across players, teams, and league-wide data. The system will serve as a foundation for building numerous data-driven applications.

---

## Data Granularity
- **At-bat level** — every at-bat for every game
- Enables custom split categories computed from at-bat-level attributes
- **Historical range:** 2021–present (expandable later)
- **Data freshness:** Daily sync (overnight batch after games complete)

---

## At-Bat Record Fields
Each at-bat row must capture the following for filtering/splitting:

### IDs (for SQL joins)
- Batter MLB ID
- Batter's team MLB ID (the team they are batting for in this at-bat)
- Pitcher MLB ID
- Pitcher's team MLB ID (the team they are pitching for in this at-bat)
- Runner(s) MLB IDs (1B, 2B, 3B)
- Ballpark MLB ID
- Game MLB ID

### Situational Context
- Batter handedness for the at-bat (L/R — switch hitters resolved to actual side)
- Pitcher handedness (L/R)
- Batting order position (1–9)
- Inning number
- Top/bottom of inning
- Outs (0/1/2)
- Runners on base (which bases occupied)
- Score (batting team & fielding team)
- Count before final pitch (balls/strikes)

### Sequences
- Pitch sequence (e.g., FB-CV-CH-SL) — ordered list of pitch types thrown
- Result sequence (e.g., S-B-F-S) — strike/ball/foul/etc. for each pitch

### Statcast / Outcome
- Exit velocity
- Launch angle
- At-bat result/event (single, strikeout, fly out, etc.)

### Game Context
- Game date
- Game time
- Ballpark (via ID, for joins)
- Home/away (derivable from top/bottom + team)
- Day/night (derivable from game time)

### Design Note
All fields must be stored as **indexed, filterable columns** (not nested JSON) to support fast filtering across millions of rows.
**Query performance on custom splits is the #1 priority.**

---

## Pitch Sequences
- **Separate `pitches` table** — one row per pitch within an at-bat
- Links to at-bat via at_bat_id
- Stores: pitch number (order), pitch type, pitch result (ball/strike/foul/in-play/etc.)
- Enables filtering like "at-bats where a curveball was thrown"
- **Statcast is at-bat level only** (exit velo, launch angle on the batted ball result) — no pitch-level Statcast

---

## Stolen Bases / Steal Attempts
- **Separate `steal_attempts` table**
- Tracks steal attempts and outcomes per game event
- Links to game, runner (MLB ID), pitcher (MLB ID), catcher (MLB ID if available)
- Fields: base attempted (2B/3B/home), success/failure, inning, outs, etc.

---

## Advanced Metrics
- **Computed on the fly** from at-bat-level data to support any custom split
- Pre-computed materialized views may be added later for common queries, but custom split flexibility is the priority

---

## Query Capabilities (High Priority)
- Stats for **players, teams, and league-wide**
- Filterable by **time periods** (e.g., 2022–2024, single season, career, custom ranges)
- Filterable by **splits** (e.g., vs LHP, vs RHP, home/away) — **custom split categories** built from at-bat data
- Filterable by **situations** (e.g., batting order position, RISP, count, inning, etc.)
- Must support combining multiple filters in a single query

---

## Stat Domains
- ✅ Batting stats (traditional + rate stats)
- ✅ Pitching stats (traditional + rate stats)
- ✅ Fielding stats
- ✅ Advanced metrics (wOBA, FIP, xBA, barrel rate, etc.)
- ✅ Statcast data (exit velocity, launch angle, spin rate, etc.)
- ✅ Game-level box score data
- ❌ Roster/transaction history (not in initial scope)
- ❌ Injury data (not in initial scope)

---

## Data Sources
- **Primary (Phase 1):** MLB Stats API (statsapi.mlb.com)
- **Future phases:** Additional sources TBD
- **ID Strategy:** All IDs for games, players, teams, and parks must match official MLB IDs

---

## Database
- **Preference:** PostgreSQL or SQLite (user is familiar with both)
- **Decision:** TBD — choose what fits best for the job
- **Notes:** Will need to handle large volumes of at-bat-level + Statcast data (2021–present)

---

## API
- **Language preference:** Python (user's comfort zone), but open to alternatives if better suited for performance
- **Performance note:** Must handle processing/aggregating large volumes of at-bat-level data on the fly
- **Consumers:** Personal apps only (single user, no multi-tenancy needed)
- **Response format:** TBD (likely JSON)
- **Auth:** TBD (low priority — single user)

---

## Infrastructure
- **Target:** Docker container (future goal)
- **Current focus:** Get the API built and functional first

---

## Open Questions
- Statcast data source — MLB API coverage vs. needing Baseball Savant supplement?
- How to handle edge cases: rain-shortened games, suspended games, doubleheaders, All-Star game, postseason?
- Should steal attempts track the catcher MLB ID (if available from MLB API)?

---

## Decisions Log
| Date       | Decision | Rationale |
|------------|----------|-----------|
| 2025-02-15 | — | Initial requirements gathering |
