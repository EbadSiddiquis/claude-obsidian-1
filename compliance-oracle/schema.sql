-- compliance-oracle/schema.sql — Hybrid Graph + Relational schema for the Compliance Oracle.
--
-- DESIGN: one SQLite file is both stores. The GRAPH is nodes+edges (authority ecosystem,
-- traversed in-process — no graph DB needed at this scale). The RELATIONAL layer maps
-- obligations -> WSP procedures -> system controls -> evidence -> attestations.
--
-- THE DISCIPLINE (inherited from the parent project's never-opine invariant): nothing in this
-- schema stores a legal conclusion. Controls resolve to satisfied/open/escalate_to_counsel/n_a/
-- satisfied_by_attestation. Generated WSPs/specs are CANDIDATES until a named principal adopts
-- them (attestations), and attestations DECAY when a pinned authority version moves.

PRAGMA foreign_keys = ON;

-- ─── GRAPH: the authority ecosystem ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS nodes (
  id             TEXT PRIMARY KEY,           -- e.g. 'cfr-17-227.303', 'cfr-12-330.7', 'finra-fp-200'
  kind           TEXT NOT NULL CHECK (kind IN
                   ('statute','rule','release','order','interpretive','enforcement',
                    'operational','system_assumption')),
  tier           TEXT NOT NULL CHECK (tier IN ('A','B','C','D','E','F')),
                                             -- A binding law · B interpretive · C adjudicative
                                             -- D operational/evidentiary · E named-human · F self
  sovereign      TEXT NOT NULL,              -- 'federal-sec' | 'fdic' | 'fincen' | 'finra' | 'state' | 'internal'
  citation       TEXT NOT NULL,              -- human citation, e.g. '17 CFR 227.303(e)'
  title          TEXT,                       -- short description
  pinned_version TEXT,                       -- eCFR amendment_date / release no. / 'manual:<date>'
  version_source TEXT NOT NULL DEFAULT 'manual',  -- 'ecfr' | 'fedreg' | 'finra' | 'manual'
  source_url     TEXT,
  fetched_at     TEXT
);

CREATE TABLE IF NOT EXISTS edges (
  src  TEXT NOT NULL REFERENCES nodes(id),
  dst  TEXT NOT NULL REFERENCES nodes(id),
  rel  TEXT NOT NULL CHECK (rel IN
        ('implements',        -- rule -> statute
         'interprets',        -- C&DI / notice / no-action -> rule (Tier B: edge, never a root)
         'supersedes',        -- newer -> older
         'cross_references',  -- THE cumulative-sovereign join (SEC custody <-> FDIC pass-through <-> BSA)
         'evidenced_by')),    -- rule -> enforcement outcome (the post-mortem link)
  note TEXT,                  -- why this edge exists, in one sentence
  PRIMARY KEY (src, dst, rel)
);

-- ─── RELATIONAL: obligations -> procedures -> controls -> evidence ──────────

CREATE TABLE IF NOT EXISTS controls (
  id          TEXT PRIMARY KEY,              -- e.g. 'oracle_custody_qualified_third_party'
  obligation  TEXT NOT NULL,                 -- the duty, in plain language
  sovereign   TEXT NOT NULL,
  severity    TEXT NOT NULL CHECK (severity IN ('gate_fatal','exemption_fatal','curable_procedural','informational')),
  cadence     TEXT NOT NULL CHECK (cadence IN ('point_in_time','continuous')),
  locus       TEXT NOT NULL CHECK (locus IN ('public','private','hybrid')),
  owner       TEXT NOT NULL,                 -- 'portal' | 'principal' | 'custodian' | 'issuer'
  eval_key    TEXT,                          -- executable evaluator name (NULL = manual)
  state       TEXT NOT NULL DEFAULT 'open' CHECK (state IN
                ('satisfied','open','escalate_to_counsel','n_a','satisfied_by_attestation'))
);

CREATE TABLE IF NOT EXISTS control_authorities (   -- provenance edges: control -> graph node
  control_id TEXT NOT NULL REFERENCES controls(id),
  node_id    TEXT NOT NULL REFERENCES nodes(id),
  pinned_version TEXT,                       -- snapshot at cite time; drift = node moved past this
  PRIMARY KEY (control_id, node_id)
);

CREATE TABLE IF NOT EXISTS wsp_procedures (        -- the Written Supervisory Procedure layer
  id          TEXT PRIMARY KEY,
  control_id  TEXT NOT NULL REFERENCES controls(id),
  status      TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN
                ('candidate','adopted','stale_reattest')),   -- candidate until a principal adopts
  who         TEXT,   -- role performing the procedure
  what        TEXT,   -- the procedure text (generated, citation-pinned)
  when_       TEXT,   -- frequency / trigger
  supervised_by TEXT, -- the supervising principal role
  evidence_artifact TEXT  -- what artifact proves it ran (log, ledger, screenshot, filing)
);

CREATE TABLE IF NOT EXISTS system_controls (       -- the technical-enforcement layer
  id          TEXT PRIMARY KEY,
  control_id  TEXT NOT NULL REFERENCES controls(id),
  spec        TEXT NOT NULL,                 -- the generated technical spec (citation-pinned)
  check_cmd   TEXT                           -- executable monitor, if wired (e.g. a script)
);

CREATE TABLE IF NOT EXISTS evidence (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  control_id  TEXT NOT NULL REFERENCES controls(id),
  captured_at TEXT NOT NULL,
  source_url  TEXT,
  summary     TEXT NOT NULL                  -- what the evidence shows (a fact, never a conclusion)
);

-- ─── HUMAN LAYER: the honest boundary, as data ──────────────────────────────

CREATE TABLE IF NOT EXISTS attestations (          -- Tier E: named-principal adoption; DECAYS on drift
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  wsp_id        TEXT NOT NULL REFERENCES wsp_procedures(id),
  principal     TEXT NOT NULL,               -- named human, of record
  adopted_at    TEXT NOT NULL,
  scope         TEXT,
  pinned_versions TEXT NOT NULL,             -- JSON {node_id: version} snapshot relied on
  fresh         INTEGER NOT NULL DEFAULT 1,  -- 0 when any pinned node drifted -> stale_reattest
  stale_reason  TEXT
);

CREATE TABLE IF NOT EXISTS assumptions (           -- Tier F: the system's own load-bearing beliefs
  id          TEXT PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('verifiable','accepted')),
  statement   TEXT NOT NULL,
  check_name  TEXT,                          -- executable check for 'verifiable'
  affects     TEXT                           -- JSON list of control ids it could corrupt
);
