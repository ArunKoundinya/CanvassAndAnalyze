-- Add per-site lists (canvass, tidytuesday). Existing subscribers are all Canvass And Analyze.
-- SQLite can't change a primary key in place, so rebuild the table with PRIMARY KEY (email, list):
-- the same address can then subscribe to each site separately, with its own token and status.
-- Run once:  npx wrangler d1 execute canvass-subscribers --remote --file=migrations/0001_lists.sql
CREATE TABLE subscribers_new (
  email           TEXT NOT NULL,                   -- lower-cased
  list            TEXT NOT NULL DEFAULT 'canvass', -- canvass | tidytuesday
  status          TEXT NOT NULL DEFAULT 'pending', -- pending | active | unsubscribed
  token           TEXT NOT NULL UNIQUE,            -- secret used in confirm/unsubscribe links
  created_at      TEXT NOT NULL,
  confirm_sent_at TEXT,
  confirmed_at    TEXT,
  unsubscribed_at TEXT,
  PRIMARY KEY (email, list)
);
INSERT INTO subscribers_new (email, list, status, token, created_at, confirm_sent_at, confirmed_at, unsubscribed_at)
  SELECT email, 'canvass', status, token, created_at, confirm_sent_at, confirmed_at, unsubscribed_at FROM subscribers;
DROP TABLE subscribers;
ALTER TABLE subscribers_new RENAME TO subscribers;
CREATE INDEX IF NOT EXISTS subscribers_list_status ON subscribers (list, status);
