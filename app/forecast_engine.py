"""
StockGuard — Inventory forecasting & alert engine (demo reconstruction)

Reads sales velocity and current stock per product from MySQL, classifies
each product into one of three alert types, and writes the result to
outputs/alerts.json for the dashboard to display.

Alert types
-----------
CRITICAL_LOW : days of inventory below the critical threshold — stockout
               risk before the next delivery from the supplier arrives.
EXCESS       : days of inventory above the excess threshold — capital
               sitting in stock that won't move for months.
STAGNANT     : zero sales in the last 30 days — capital locked in dead stock.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'demo_user'),
    'password': os.getenv('DB_PASSWORD', 'demo_password'),
    'database': os.getenv('DB_NAME', 'stockguard_demo'),
}

CRITICAL_DAYS = 15   # below this many days of stock → stockout risk
EXCESS_DAYS = 90     # above this many days of stock → capital tied up
STAGNANT_DAYS = 30   # no sales in this window → considered dead stock

OUTPUT_PATH = Path(__file__).parent / 'outputs' / 'alerts.json'


class StockGuardForecast:
    def __init__(self):
        self.conn = None
        self.alerts: List[Dict] = []

    def connect(self) -> bool:
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            return True
        except Exception as e:
            print(f"DB connection failed: {e}")
            return False

    def fetch_inventory_metrics(self) -> List[Dict]:
        query = """
            SELECT
                m.product_id, m.name, m.sku, m.category, p.unit_cost AS unit_price,
                m.lead_time_days, m.current_stock, m.sales_last_30d AS sales_last_30_days,
                m.days_of_inventory,
                ROUND(m.sales_last_30d / 30.0, 2) AS daily_avg_sales
            FROM v_inventory_metrics m
            JOIN products p ON p.product_id = m.product_id
            ORDER BY m.days_of_inventory ASC, m.current_stock DESC;
        """
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def analyze_product(self, product: Dict) -> Optional[Dict]:
        name = product['name']
        sku = product['sku']
        category = product['category']
        current_stock = int(product['current_stock'] or 0)
        lead_time = int(product['lead_time_days'] or 0)
        days_inventory = float(product['days_of_inventory']) if product['days_of_inventory'] is not None else None
        daily_avg = float(product['daily_avg_sales'] or 0)
        sales_30d = int(product['sales_last_30_days'] or 0)
        unit_price = float(product['unit_price'] or 0)

        base = {
            'product_id': product['product_id'],
            'product': {'name': name, 'sku': sku, 'category': category},
            'current_stock': current_stock,
            'sales_last_30d': sales_30d,
            'daily_avg_sales': round(daily_avg, 2),
            'lead_time_days': lead_time,
        }

        # No sales at all in the window — dead stock
        if sales_30d == 0 and current_stock > 0:
            capital_locked = round(current_stock * unit_price, 2)
            return {
                **base,
                'alert_type': 'STAGNANT',
                'severity': 'medium',
                'days_of_inventory': None,
                'capital_locked': capital_locked,
                'recommendation': (
                    f'No sales in {STAGNANT_DAYS} days. ${capital_locked:,.2f} locked in stock. '
                    'Consider a promotion or discontinuing the product.'
                ),
                'priority': 3,
            }

        if days_inventory is None:
            return None

        # Stockout risk: not enough stock to cover the supplier lead time
        if days_inventory < CRITICAL_DAYS:
            suggested_order = max(0, int(round(daily_avg * lead_time - current_stock)))
            lost_sales_risk = round(daily_avg * lead_time * unit_price, 2)
            return {
                **base,
                'alert_type': 'CRITICAL_LOW',
                'severity': 'critical',
                'days_of_inventory': days_inventory,
                'suggested_order': suggested_order,
                'lost_sales_risk': lost_sales_risk,
                'recommendation': (
                    f'Only {days_inventory} days of stock left, supplier lead time is {lead_time} days. '
                    f'Order {suggested_order} units now to avoid a stockout (risk: ${lost_sales_risk:,.2f}).'
                ),
                'priority': 1,
            }

        # Too much stock: capital tied up, won't move for months
        if days_inventory > EXCESS_DAYS:
            excess_units = max(0, int(round(current_stock - daily_avg * 60)))
            capital_excess = round(excess_units * unit_price, 2)
            return {
                **base,
                'alert_type': 'EXCESS',
                'severity': 'high',
                'days_of_inventory': days_inventory,
                'excess_units': excess_units,
                'capital_excess': capital_excess,
                'recommendation': (
                    f'{days_inventory} days of stock on hand — ${capital_excess:,.2f} tied up '
                    f'in {excess_units} units beyond a healthy 60-day level. Reduce next orders.'
                ),
                'priority': 2,
            }

        return None

    def run(self) -> bool:
        if not self.connect():
            return False

        products = self.fetch_inventory_metrics()
        self.alerts = [a for a in (self.analyze_product(p) for p in products) if a]
        self.alerts.sort(key=lambda a: a['priority'])
        return True

    def save(self) -> Dict:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        output = {
            'generated_at': datetime.now().isoformat(),
            'total_alerts': len(self.alerts),
            'critical_count': sum(1 for a in self.alerts if a['severity'] == 'critical'),
            'high_count': sum(1 for a in self.alerts if a['severity'] == 'high'),
            'medium_count': sum(1 for a in self.alerts if a['severity'] == 'medium'),
            'alerts': self.alerts,
        }
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return output


def main():
    engine = StockGuardForecast()
    if not engine.run():
        raise SystemExit(1)
    output = engine.save()
    print(f"{output['total_alerts']} alerts generated "
          f"({output['critical_count']} critical, {output['high_count']} high, {output['medium_count']} medium)")


if __name__ == '__main__':
    main()
