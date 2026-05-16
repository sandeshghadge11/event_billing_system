CREATE DATABASE IF NOT EXISTS event_billing;
USE event_billing;

CREATE TABLE IF NOT EXISTS clients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  mobile VARCHAR(20) NOT NULL,
  address VARCHAR(255),
  notes VARCHAR(500),
  created_at DATETIME NOT NULL,
  INDEX ix_clients_name (name),
  INDEX ix_clients_mobile (mobile)
);

CREATE TABLE IF NOT EXISTS items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(80) NOT NULL,
  unit VARCHAR(40) NOT NULL,
  default_rate DECIMAL(12, 2) NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL,
  INDEX ix_items_name (name)
);

CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_no VARCHAR(40) NOT NULL UNIQUE,
  title VARCHAR(160) NOT NULL,
  client_id INT NOT NULL,
  start_date DATE,
  end_date DATE,
  status VARCHAR(30) NOT NULL,
  notes VARCHAR(500),
  created_at DATETIME NOT NULL,
  FOREIGN KEY (client_id) REFERENCES clients(id),
  INDEX ix_bookings_booking_no (booking_no)
);

CREATE TABLE IF NOT EXISTS booking_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  name VARCHAR(80) NOT NULL,
  event_date DATE,
  venue VARCHAR(160),
  event_time VARCHAR(80),
  notes VARCHAR(500),
  FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_line_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  item_id INT,
  material_name VARCHAR(120) NOT NULL,
  quantity DECIMAL(12, 2) NOT NULL,
  rate DECIMAL(12, 2) NOT NULL,
  notes VARCHAR(500),
  FOREIGN KEY (event_id) REFERENCES booking_events(id) ON DELETE CASCADE,
  FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  amount DECIMAL(12, 2) NOT NULL,
  payment_date DATE,
  mode VARCHAR(40) NOT NULL,
  notes VARCHAR(500),
  FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);
