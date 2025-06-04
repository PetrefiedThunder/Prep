INSERT INTO users (email, name, password, role) VALUES
('host@example.com', 'Kitchen Host', 'test123', 'host'),
('user@example.com', 'Renter', 'test123', 'renter');

INSERT INTO kitchens (host_id, name, address, cert_level, pricing, equipment)
VALUES
(1, 'Sunrise Kitchen', '123 Echo Park Ave', 'A', 25, ARRAY['oven', 'sink', 'griddle']),
(1, 'Midnight Bakery', '456 Sunset Blvd', 'B', 18, ARRAY['oven', 'fridge']);
