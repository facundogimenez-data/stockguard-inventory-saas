-- ============================================================
-- STOCKGUARD DEMO — Schema + synthetic seed data
-- ============================================================
-- Demo dataset for a fictional food/grocery distributor.
-- Product catalog and sales/inventory figures are synthetic,
-- generated to reproduce the alert patterns StockGuard detects
-- in real deployments (critical stockout risk, excess inventory,
-- stagnant products) without using any real client data.
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    product_id      INT PRIMARY KEY,
    sku             VARCHAR(20) NOT NULL,
    name            VARCHAR(120) NOT NULL,
    category        VARCHAR(60) NOT NULL,
    unit_cost       DECIMAL(10,2) NOT NULL,
    selling_price   DECIMAL(10,2) NOT NULL,
    reorder_point   INT NOT NULL,
    lead_time_days  INT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id         INT AUTO_INCREMENT PRIMARY KEY,
    product_id      INT NOT NULL,
    quantity        INT NOT NULL,
    sale_date       DATE NOT NULL,
    unit_price      DECIMAL(10,2) NOT NULL,
    customer_type   VARCHAR(20) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id     INT AUTO_INCREMENT PRIMARY KEY,
    product_id      INT NOT NULL,
    movement_type   ENUM('IN', 'OUT') NOT NULL,
    quantity        INT NOT NULL,
    movement_date   DATE NOT NULL,
    source          VARCHAR(40),
    reference       VARCHAR(60),
    notes           VARCHAR(200),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- View consumed by the dashboard and the forecast engine: rolls up
-- current stock and last-30-day sales velocity per product.
CREATE OR REPLACE VIEW v_inventory_metrics AS
SELECT
    p.product_id,
    p.name,
    p.sku,
    p.category,
    p.unit_cost,
    p.lead_time_days,
    COALESCE(inv.current_stock, 0)                                      AS current_stock,
    COALESCE(sl.sales_last_30d, 0)                                      AS sales_last_30d,
    CASE
        WHEN COALESCE(sl.sales_last_30d, 0) > 0
        THEN ROUND(COALESCE(inv.current_stock, 0) / (sl.sales_last_30d / 30.0), 1)
        ELSE NULL
    END                                                                 AS days_of_inventory
FROM products p
LEFT JOIN (
    SELECT product_id,
           SUM(CASE WHEN movement_type = 'IN' THEN quantity ELSE -quantity END) AS current_stock
    FROM inventory_movements
    GROUP BY product_id
) inv ON inv.product_id = p.product_id
LEFT JOIN (
    SELECT product_id, SUM(quantity) AS sales_last_30d
    FROM sales
    WHERE sale_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    GROUP BY product_id
) sl ON sl.product_id = p.product_id;

-- ------------------------------------------------------------
-- SEED: product catalog (synthetic food/grocery distributor)
-- ------------------------------------------------------------
INSERT INTO products (product_id, sku, name, category, unit_cost, selling_price, reorder_point, lead_time_days) VALUES
(2,  'ACE-OLI-002', 'Aceite Oliva Extra Virgen', 'Aceites',        8.50, 12.90, 30, 10),
(45, 'ATU-LOM-045', 'Atún Lomito',              'Conservas',       3.80,  6.50, 40, 60),
(97, 'CAF-MOL-097', 'Café Molido',              'Almacén',         5.50,  9.00, 35, 20),
(94, 'VIN-TIN-094', 'Vino Tinto',               'Bebidas',         8.50, 14.00, 25, 15),
(87, 'NUE-VAR-087', 'Nueces',                   'Frutos Secos',    7.80, 12.50, 30, 18),
(72, 'QUE-AZU-072', 'Queso Azul',               'Lácteos',        15.00, 22.00, 20, 10),
(23, 'QUI-GRA-023', 'Quinoa',                   'Almacén',         5.50,  8.90, 25, 20),
(95, 'VIN-BLA-095', 'Vino Blanco',              'Bebidas',         7.80, 13.00, 25, 15),
(70, 'QUE-SAR-070', 'Queso Sardo',              'Lácteos',        11.50, 17.50, 20,  7),
(33, 'RAV-CAR-033', 'Ravioles Carne',           'Pastas',          4.50,  7.20, 30,  3),
(75, 'ALF-DOC-075', 'Alfajores',                'Golosinas',       4.50,  7.50, 30, 12),
(11, 'PIM-NEG-011', 'Pimienta Negra',           'Especias',        4.20,  6.90, 30, 45),
(5,  'MAY-CLA-005', 'Mayonesa',                 'Almacén',         2.80,  4.50, 35,  8),
(43, 'TOM-TRI-043', 'Tomate Triturado',         'Conservas',       1.80,  3.20, 40, 15),
(91, 'JUG-NAR-091', 'Jugo Naranja',             'Bebidas',         1.90,  3.20, 200, 12),
(16, 'ARR-BLA-016', 'Arroz Blanco',             'Almacén',         1.50,  2.60, 200, 20),
(31, 'FID-GUI-031', 'Fideos Guiseros',          'Pastas',          1.40,  2.40, 200, 15),
(76, 'CHO-BAR-076', 'Chocolate Barra',          'Golosinas',       2.20,  3.80, 150, 18),
(32, 'GNO-PAP-032', 'Ñoquis',                   'Pastas',          2.10,  3.60, 150, 10),
(74, 'GAL-SAL-074', 'Galletitas Saladas',       'Almacén',         1.60,  2.80, 120, 15),
(61, 'LEC-ENT-061', 'Leche Entera',             'Lácteos',         0.95,  1.60, 200,  5),
(92, 'JUG-MAN-092', 'Jugo Manzana',             'Bebidas',         1.90,  3.20, 150, 12),
(46, 'ARV-LAT-046', 'Arvejas Lata',             'Conservas',       1.20,  2.10, 150, 20),
(98, 'AGU-SAB-098', 'Agua Saborizada',          'Bebidas',         1.10,  1.90, 200, 10),
(42, 'RAV-RIC-042', 'Ravioles Ricota',          'Pastas',          4.30,  6.90, 80,  3),
(50, 'ACE-NEG-050', 'Aceitunas Negras',         'Conservas',       3.50,  5.80, 50, 25),
(53, 'DUR-LAT-053', 'Duraznos',                 'Conservas',       2.40,  4.10, 60, 20);

-- ------------------------------------------------------------
-- SEED: opening stock — IN movement 90 days ago for every SKU
-- ------------------------------------------------------------
INSERT INTO inventory_movements (product_id, movement_type, quantity, movement_date, source, reference, notes)
SELECT product_id, 'IN', stock_qty, DATE_SUB(CURDATE(), INTERVAL 90 DAY), 'purchase_order', CONCAT('PO-', LPAD(product_id, 4, '0')), 'Initial stock load'
FROM (VALUES
    ROW(2, 10),  ROW(45, 10), ROW(97, 10), ROW(94, 4),  ROW(87, 10),
    ROW(72, 3),  ROW(23, 5),  ROW(95, 10), ROW(70, 6),  ROW(33, 3),
    ROW(75, 3),  ROW(11, 14), ROW(5, 5),   ROW(43, 12),
    ROW(91, 380),ROW(16, 240),ROW(31, 290),ROW(76, 150),ROW(32, 170),
    ROW(74, 110),ROW(61, 260),ROW(92, 95), ROW(46, 70), ROW(98, 75),
    ROW(42, 60), ROW(50, 30), ROW(53, 40)
) AS seed(product_id, stock_qty);

-- ------------------------------------------------------------
-- SEED: sales — last 30 days, calibrated to reproduce three
-- alert patterns (CRITICAL_LOW, EXCESS, STAGNANT)
-- ------------------------------------------------------------

-- CRITICAL_LOW: high daily velocity vs. low stock + long lead times
INSERT INTO sales (product_id, quantity, sale_date, unit_price, customer_type) VALUES
(45, 8, DATE_SUB(CURDATE(), INTERVAL 1 DAY),  6.50, 'retail'),
(45, 12, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 6.50, 'wholesale'),
(45, 6, DATE_SUB(CURDATE(), INTERVAL 4 DAY),  6.50, 'retail'),
(45, 10, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 6.50, 'distributor'),
(45, 8, DATE_SUB(CURDATE(), INTERVAL 8 DAY),  6.50, 'retail'),
(45, 12, DATE_SUB(CURDATE(), INTERVAL 10 DAY),6.50, 'wholesale'),
(45, 7, DATE_SUB(CURDATE(), INTERVAL 13 DAY), 6.50, 'retail'),
(2, 15, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 12.90, 'wholesale'),
(2, 10, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 12.90, 'retail'),
(2, 18, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 12.90, 'distributor'),
(2, 12, DATE_SUB(CURDATE(), INTERVAL 7 DAY), 12.90, 'retail'),
(2, 8, DATE_SUB(CURDATE(), INTERVAL 10 DAY), 12.90, 'wholesale'),
(97, 10, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 9.00, 'retail'),
(97, 8, DATE_SUB(CURDATE(), INTERVAL 3 DAY),  9.00, 'wholesale'),
(97, 12, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 9.00, 'retail'),
(97, 15, DATE_SUB(CURDATE(), INTERVAL 8 DAY), 9.00, 'distributor'),
(94, 8, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 14.00, 'retail'),
(94, 6, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 14.00, 'wholesale'),
(94, 10, DATE_SUB(CURDATE(), INTERVAL 7 DAY),14.00, 'retail'),
(87, 6, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 12.50, 'retail'),
(87, 9, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 12.50, 'wholesale'),
(87, 7, DATE_SUB(CURDATE(), INTERVAL 8 DAY), 12.50, 'retail'),
(72, 2, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 22.00, 'retail'),
(72, 1, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 22.00, 'retail'),
(23, 4, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 8.90, 'retail'),
(23, 3, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 8.90, 'wholesale'),
(95, 8, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 13.00, 'retail'),
(95, 6, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 13.00, 'wholesale'),
(70, 5, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 17.50, 'retail'),
(70, 4, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 17.50, 'distributor'),
(33, 3, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 7.20, 'retail'),
(33, 2, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 7.20, 'wholesale'),
(75, 3, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 7.50, 'retail'),
(75, 2, DATE_SUB(CURDATE(), INTERVAL 7 DAY), 7.50, 'retail');

-- HEALTHY: moderate, balanced velocity (no alert expected)
INSERT INTO sales (product_id, quantity, sale_date, unit_price, customer_type) VALUES
(11, 1, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 6.90, 'retail'),
(11, 1, DATE_SUB(CURDATE(), INTERVAL 9 DAY), 6.90, 'wholesale'),
(5, 4, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 4.50, 'retail'),
(5, 3, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 4.50, 'wholesale'),
(5, 2, DATE_SUB(CURDATE(), INTERVAL 11 DAY), 4.50, 'retail'),
(43, 6, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 3.20, 'retail'),
(43, 5, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 3.20, 'distributor'),
(43, 4, DATE_SUB(CURDATE(), INTERVAL 9 DAY), 3.20, 'retail');

-- EXCESS: large opening stock vs. modest sales (>90 days coverage)
INSERT INTO sales (product_id, quantity, sale_date, unit_price, customer_type) VALUES
(91, 12, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 3.20, 'retail'),
(91, 10, DATE_SUB(CURDATE(), INTERVAL 9 DAY), 3.20, 'wholesale'),
(91, 8,  DATE_SUB(CURDATE(), INTERVAL 17 DAY),3.20, 'retail'),
(16, 9,  DATE_SUB(CURDATE(), INTERVAL 3 DAY), 2.60, 'retail'),
(16, 7,  DATE_SUB(CURDATE(), INTERVAL 12 DAY),2.60, 'wholesale'),
(31, 11, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 2.40, 'retail'),
(31, 8,  DATE_SUB(CURDATE(), INTERVAL 14 DAY),2.40, 'distributor'),
(76, 6,  DATE_SUB(CURDATE(), INTERVAL 5 DAY), 3.80, 'retail'),
(76, 5,  DATE_SUB(CURDATE(), INTERVAL 16 DAY),3.80, 'retail'),
(32, 7,  DATE_SUB(CURDATE(), INTERVAL 6 DAY), 3.60, 'wholesale'),
(74, 5,  DATE_SUB(CURDATE(), INTERVAL 7 DAY), 2.80, 'retail'),
(61, 14, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 1.60, 'retail'),
(61, 12, DATE_SUB(CURDATE(), INTERVAL 9 DAY), 1.60, 'wholesale'),
(92, 6,  DATE_SUB(CURDATE(), INTERVAL 8 DAY), 3.20, 'retail'),
(46, 4,  DATE_SUB(CURDATE(), INTERVAL 10 DAY),2.10, 'retail'),
(98, 9,  DATE_SUB(CURDATE(), INTERVAL 6 DAY), 1.90, 'retail');

-- STAGNANT: zero sales in the last 30 days, capital locked in stock
-- (product_ids 42, 50, 53 intentionally have NO rows in `sales`)
