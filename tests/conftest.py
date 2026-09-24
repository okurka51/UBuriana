import datetime

import pytest

from model.database import DBManager


@pytest.fixture
def db():
    return DBManager(":memory:")


@pytest.fixture
def today():
    return datetime.date(2026, 10, 15)


@pytest.fixture
def populated(db):
    """DB with customers Marek, Petr and menu items PZ1, BG2; returns (db, name/code -> id)."""
    db.add_customer("Marek", "blue")
    db.add_customer("Petr", "red")
    db.add_menu_item("PZ1", "Margherita")
    db.add_menu_item("BG2", "Burger")

    ids = {c.name: c.id for c in db.get_all_customers()}
    ids.update({i.code: i.id for i in db.get_all_menu_items()})
    return db, ids
