"""Build data/company.db, the sample database that query_database() reads.

Run once:  py data/seed_db.py
Re-running deletes and rebuilds the database, so it is always in a known state.
"""

import random
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "company.db"

DEPARTMENTS = [
    (1, "Engineering", "Berlin"),
    (2, "Sales", "London"),
    (3, "Marketing", "London"),
    (4, "Support", "Lisbon"),
    (5, "Finance", "Berlin"),
]

# (name, department_id, title, salary, hire_date)
EMPLOYEES = [
    ("Ada Park", 1, "Staff Engineer", 128000, "2017-03-14"),
    ("Ben Ortiz", 1, "Senior Engineer", 112000, "2019-07-01"),
    ("Chloe Nakamura", 1, "Engineer", 94000, "2022-01-10"),
    ("Dev Raman", 1, "Engineer", 91000, "2023-05-22"),
    ("Elif Kaya", 1, "Engineering Manager", 135000, "2016-11-03"),
    ("Femi Adeyemi", 1, "Junior Engineer", 72000, "2025-02-17"),
    ("Grace Liu", 2, "Account Executive", 78000, "2020-04-06"),
    ("Hugo Martin", 2, "Account Executive", 81000, "2021-09-13"),
    ("Isla Brown", 2, "Sales Manager", 104000, "2018-02-26"),
    ("Jonas Weber", 2, "Sales Development Rep", 58000, "2024-06-03"),
    ("Kira Novak", 3, "Marketing Manager", 98000, "2019-10-21"),
    ("Liam O'Neill", 3, "Content Strategist", 69000, "2022-08-15"),
    ("Maya Rossi", 3, "Designer", 76000, "2021-03-29"),
    ("Nico Silva", 4, "Support Lead", 67000, "2018-12-10"),
    ("Olga Petrova", 4, "Support Specialist", 52000, "2023-01-16"),
    ("Pedro Costa", 4, "Support Specialist", 50000, "2024-09-02"),
    ("Quinn Taylor", 4, "Support Specialist", 51000, "2025-04-14"),
    ("Rosa Jimenez", 5, "Finance Director", 142000, "2015-06-08"),
    ("Sam Okafor", 5, "Accountant", 74000, "2020-11-30"),
]

PRODUCTS = [("Atlas", 12), ("Beacon", 25), ("Compass", 18)]
CUSTOMERS = ["Acme Corp", "Globex", "Initech", "Umbrella", "Hooli", "Stark Industries",
             "Wayne Enterprises", "Wonka Foods", "Cyberdyne", "Soylent Co"]


def build() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE departments (
            id       INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            location TEXT NOT NULL
        );
        CREATE TABLE employees (
            id            INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            title         TEXT NOT NULL,
            salary        INTEGER NOT NULL,   -- yearly, in USD
            hire_date     TEXT NOT NULL       -- ISO date
        );
        CREATE TABLE orders (
            id          INTEGER PRIMARY KEY,
            customer    TEXT NOT NULL,
            product     TEXT NOT NULL,        -- Atlas, Beacon or Compass
            seats       INTEGER NOT NULL,
            amount      REAL NOT NULL,        -- USD per month
            order_date  TEXT NOT NULL,        -- ISO date
            sales_rep_id INTEGER REFERENCES employees(id)
        );
        """
    )
    conn.executemany("INSERT INTO departments VALUES (?, ?, ?)", DEPARTMENTS)
    conn.executemany(
        "INSERT INTO employees (name, department_id, title, salary, hire_date) VALUES (?, ?, ?, ?, ?)",
        EMPLOYEES,
    )

    # Fixed seed so every run produces exactly the same orders.
    rng = random.Random(42)
    sales_rep_ids = [7, 8, 9, 10]
    orders = []
    for _ in range(60):
        product, price = rng.choice(PRODUCTS)
        seats = rng.randint(5, 200)
        date = f"{rng.choice([2023, 2024, 2025, 2026])}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        orders.append((rng.choice(CUSTOMERS), product, seats, seats * price, date, rng.choice(sales_rep_ids)))
    conn.executemany(
        "INSERT INTO orders (customer, product, seats, amount, order_date, sales_rep_id) VALUES (?, ?, ?, ?, ?, ?)",
        orders,
    )

    conn.commit()
    conn.close()
    print(f"Built {DB_PATH} with {len(DEPARTMENTS)} departments, {len(EMPLOYEES)} employees, {len(orders)} orders.")


if __name__ == "__main__":
    build()
