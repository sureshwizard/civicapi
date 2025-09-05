-- file: /home/sureshwizard/projects/liveprojects/civicapi/backend/schema.sql

PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS bills (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT NOT NULL,
  description   TEXT,
  amount        REAL NOT NULL DEFAULT 0,
  currency      TEXT NOT NULL DEFAULT 'INR',
  due_date      TEXT NOT NULL,                 -- ISO8601 date (YYYY-MM-DD) or datetime
  status        TEXT NOT NULL DEFAULT 'unpaid',-- 'unpaid' | 'paid' | 'overdue' (your code may just check 'paid')
  paid_at       TEXT,                          -- ISO8601 timestamp when marked paid
  reference     TEXT,                          -- external ref / invoice #
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Helpful index for your list/order
CREATE INDEX IF NOT EXISTS idx_bills_due_date ON bills(due_date);
CREATE INDEX IF NOT EXISTS idx_bills_status   ON bills(status);

-- Optional: seed a few rows so GET /bills returns data
INSERT INTO bills (title, description, amount, currency, due_date, status)
VALUES
  ('Water Bill', 'August cycle', 350.00, 'INR', date('now','+3 days'), 'unpaid'),
  ('Internet Bill', 'Fiber 300Mbps', 999.00, 'INR', date('now','+5 days'), 'unpaid'),
  ('Electricity', 'TN 2BHK', 1420.50, 'INR', date('now','-2 days'), 'unpaid');

