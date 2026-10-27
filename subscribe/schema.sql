-- Subscribers of Arun's sites. One row per email address per list (site).
-- (Databases created before lists existed: run migrations/0001_lists.sql instead.)
CREATE TABLE IF NOT EXISTS subscribers (
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
CREATE INDEX IF NOT EXISTS subscribers_list_status ON subscribers (list, status);
