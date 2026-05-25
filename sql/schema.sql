-- ============================================================================
-- MLB Database Schema (PostgreSQL)
-- Reference SQL — tables are also created via SQLAlchemy models.
-- ============================================================================

-- Players
CREATE TABLE IF NOT EXISTS players (
    mlb_id          INTEGER PRIMARY KEY,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    primary_number  VARCHAR(10),
    birth_date      DATE,
    bat_side        VARCHAR(1),          -- L, R, S
    pitch_hand      VARCHAR(1),          -- L, R
    primary_position VARCHAR(5),
    mlb_debut_date  DATE,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

-- Teams
CREATE TABLE IF NOT EXISTS teams (
    mlb_id          INTEGER PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    team_name       VARCHAR(50) NOT NULL,
    abbreviation    VARCHAR(5) NOT NULL,
    league_name     VARCHAR(50),
    division_name   VARCHAR(50),
    venue_mlb_id    INTEGER REFERENCES parks(mlb_id),
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

-- Parks / Venues
CREATE TABLE IF NOT EXISTS parks (
    mlb_id          INTEGER PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    city            VARCHAR(100),
    state           VARCHAR(50),
    capacity        SMALLINT,
    surface_type    VARCHAR(30),
    roof_type       VARCHAR(30)
);

-- Games
CREATE TABLE IF NOT EXISTS games (
    mlb_game_id     INTEGER PRIMARY KEY,
    game_date       DATE NOT NULL,
    game_datetime   TIMESTAMPTZ,
    season          SMALLINT NOT NULL,
    game_type       VARCHAR(2) NOT NULL,    -- R, P, S, A, etc.
    status          VARCHAR(30) NOT NULL,
    day_night       VARCHAR(10),
    home_team_mlb_id INTEGER NOT NULL REFERENCES teams(mlb_id),
    away_team_mlb_id INTEGER NOT NULL REFERENCES teams(mlb_id),
    home_score      SMALLINT,
    away_score      SMALLINT,
    park_mlb_id     INTEGER REFERENCES parks(mlb_id),
    double_header   VARCHAR(1),
    game_number     SMALLINT DEFAULT 1,
    innings_played  SMALLINT
);

CREATE INDEX IF NOT EXISTS ix_games_date ON games(game_date);
CREATE INDEX IF NOT EXISTS ix_games_season ON games(season);
CREATE INDEX IF NOT EXISTS ix_games_type ON games(game_type);
CREATE INDEX IF NOT EXISTS ix_games_home_team ON games(home_team_mlb_id);
CREATE INDEX IF NOT EXISTS ix_games_away_team ON games(away_team_mlb_id);

-- At-Bats (core table for stat queries)
CREATE TABLE IF NOT EXISTS at_bats (
    id                      SERIAL PRIMARY KEY,
    game_mlb_id             INTEGER NOT NULL REFERENCES games(mlb_game_id),
    game_date               DATE NOT NULL,
    season                  SMALLINT NOT NULL,
    game_type               VARCHAR(2) NOT NULL DEFAULT 'R',
    park_mlb_id             INTEGER REFERENCES parks(mlb_id),
    day_night               VARCHAR(10),
    at_bat_number           SMALLINT NOT NULL,
    batter_mlb_id           INTEGER NOT NULL REFERENCES players(mlb_id),
    batter_team_mlb_id      INTEGER NOT NULL REFERENCES teams(mlb_id),
    pitcher_mlb_id          INTEGER NOT NULL REFERENCES players(mlb_id),
    pitcher_team_mlb_id     INTEGER NOT NULL REFERENCES teams(mlb_id),
    batter_is_home          BOOLEAN NOT NULL,
    bat_side                VARCHAR(1) NOT NULL,    -- L or R
    pitch_hand              VARCHAR(1) NOT NULL,    -- L or R
    inning                  SMALLINT NOT NULL,
    half_inning             VARCHAR(6) NOT NULL,    -- 'top' or 'bottom'
    batting_order_position  SMALLINT NOT NULL,
    outs_before             SMALLINT NOT NULL,
    runner_on_1b_mlb_id     INTEGER REFERENCES players(mlb_id),
    runner_on_2b_mlb_id     INTEGER REFERENCES players(mlb_id),
    runner_on_3b_mlb_id     INTEGER REFERENCES players(mlb_id),
    batting_team_score      SMALLINT NOT NULL DEFAULT 0,
    fielding_team_score     SMALLINT NOT NULL DEFAULT 0,
    balls                   SMALLINT NOT NULL DEFAULT 0,
    strikes                 SMALLINT NOT NULL DEFAULT 0,
    event                   VARCHAR(60) NOT NULL,
    event_type              VARCHAR(40) NOT NULL,
    rbi                     SMALLINT NOT NULL DEFAULT 0,
    outs_on_play            SMALLINT NOT NULL DEFAULT 0,
    hit_exit_velocity       REAL,
    hit_launch_angle        REAL,
    hit_distance            REAL,
    hit_trajectory          VARCHAR(20),
    description             TEXT
);

-- Single-column indexes
CREATE INDEX IF NOT EXISTS ix_at_bats_game_mlb_id    ON at_bats(game_mlb_id);
CREATE INDEX IF NOT EXISTS ix_at_bats_batter_mlb_id  ON at_bats(batter_mlb_id);
CREATE INDEX IF NOT EXISTS ix_at_bats_pitcher_mlb_id ON at_bats(pitcher_mlb_id);
CREATE INDEX IF NOT EXISTS ix_at_bats_game_date      ON at_bats(game_date);
CREATE INDEX IF NOT EXISTS ix_at_bats_season         ON at_bats(season);
CREATE INDEX IF NOT EXISTS ix_at_bats_batter_team    ON at_bats(batter_team_mlb_id);
CREATE INDEX IF NOT EXISTS ix_at_bats_pitcher_team   ON at_bats(pitcher_team_mlb_id);
CREATE INDEX IF NOT EXISTS ix_at_bats_park           ON at_bats(park_mlb_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_at_bats_batter_season      ON at_bats(batter_mlb_id, season);
CREATE INDEX IF NOT EXISTS ix_at_bats_batter_date        ON at_bats(batter_mlb_id, game_date);
CREATE INDEX IF NOT EXISTS ix_at_bats_pitcher_season     ON at_bats(pitcher_mlb_id, season);
CREATE INDEX IF NOT EXISTS ix_at_bats_batter_team_season ON at_bats(batter_team_mlb_id, season);
CREATE INDEX IF NOT EXISTS ix_at_bats_splits             ON at_bats(bat_side, pitch_hand);
CREATE INDEX IF NOT EXISTS ix_at_bats_season_type        ON at_bats(season, game_type);

-- Unique constraint to prevent duplicate ingestion
CREATE UNIQUE INDEX IF NOT EXISTS uq_at_bats_game_atbat ON at_bats(game_mlb_id, at_bat_number);

-- Pitches
CREATE TABLE IF NOT EXISTS pitches (
    id                      SERIAL PRIMARY KEY,
    at_bat_id               INTEGER NOT NULL REFERENCES at_bats(id) ON DELETE CASCADE,
    pitch_number            SMALLINT NOT NULL,
    pitch_type              VARCHAR(10),
    pitch_type_description  VARCHAR(40),
    pitch_result            VARCHAR(2) NOT NULL,
    pitch_result_description VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS ix_pitches_at_bat_id ON pitches(at_bat_id);
CREATE INDEX IF NOT EXISTS ix_pitches_pitch_type ON pitches(pitch_type);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pitches_at_bat_num ON pitches(at_bat_id, pitch_number);

-- Steal Attempts
CREATE TABLE IF NOT EXISTS steal_attempts (
    id                  SERIAL PRIMARY KEY,
    game_mlb_id         INTEGER NOT NULL REFERENCES games(mlb_game_id),
    game_date           DATE NOT NULL,
    season              SMALLINT NOT NULL,
    inning              SMALLINT NOT NULL,
    half_inning         VARCHAR(6) NOT NULL,
    runner_mlb_id       INTEGER NOT NULL REFERENCES players(mlb_id),
    runner_team_mlb_id  INTEGER NOT NULL REFERENCES teams(mlb_id),
    pitcher_mlb_id      INTEGER NOT NULL REFERENCES players(mlb_id),
    catcher_mlb_id      INTEGER REFERENCES players(mlb_id),
    attempted_base      VARCHAR(4) NOT NULL,
    is_successful       BOOLEAN NOT NULL,
    outs_before         SMALLINT,
    description         TEXT
);

CREATE INDEX IF NOT EXISTS ix_steal_game    ON steal_attempts(game_mlb_id);
CREATE INDEX IF NOT EXISTS ix_steal_runner  ON steal_attempts(runner_mlb_id);
CREATE INDEX IF NOT EXISTS ix_steal_runner_season ON steal_attempts(runner_mlb_id, season);
CREATE INDEX IF NOT EXISTS ix_steal_pitcher ON steal_attempts(pitcher_mlb_id);
CREATE INDEX IF NOT EXISTS ix_steal_date    ON steal_attempts(game_date);
