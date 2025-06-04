CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  name TEXT,
  password TEXT,
  role TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE kitchens (
  id SERIAL PRIMARY KEY,
  host_id INT REFERENCES users(id),
  name TEXT,
  address TEXT,
  cert_level TEXT,
  pricing NUMERIC,
  equipment TEXT[],
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bookings (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  kitchen_id INT REFERENCES kitchens(id),
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  status TEXT DEFAULT 'pending'
);
