CREATE TABLE provenance_items(
  id UUID PRIMARY KEY,
  type TEXT NOT NULL,
  hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  parent_hash TEXT,
  metadata JSONB
);

CREATE TABLE anchors(
  id UUID PRIMARY KEY,
  merkle_root TEXT NOT NULL,
  chain TEXT NOT NULL,
  txid TEXT,
  anchored_at TIMESTAMPTZ
);
