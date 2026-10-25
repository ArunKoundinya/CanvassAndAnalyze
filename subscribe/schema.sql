-- Subscribers of Canvass And Analyze. One row per email address.
CREATE TABLE IF NOT EXISTS subscribers (
  email           TEXT PRIMARY KEY,                -- lower-cased
  status          TEXT NOT NULL DEFAULT 'pending', -- pending | active | unsubscribed
  token           TEXT NOT NULL UNIQUE,            -- secret used in confirm/unsubscribe links
  created_at      TEXT NOT NULL,
  confirm_sent_at TEXT,
  confirmed_at    TEXT,
  unsubscribed_at TEXT
);
CREATE INDEX IF NOT EXISTS subscribers_status ON subscribers (status);
