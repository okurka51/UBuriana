import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from model.helpers import CustomerDTO, CustomerOrdersDTO, OrderDTO


# region CUSTOMER

class TestCustomers:
    def test_add_customer_returns_id(self, db):
        new_id = db.add_customer("Jana", "green")
        assert db.get_customer(new_id).name == "Jana"

    def test_empty_database_has_no_customers(self, db):
        assert db.get_all_customers() == []

    def test_add_and_get_customer(self, db):
        db.add_customer("Marek", "blue")

        [customer] = db.get_all_customers()
        assert customer.name == "Marek"
        assert customer.color == "blue"
        assert db.get_customer(customer.id) == customer

    def test_get_missing_customer_returns_none(self, db):
        assert db.get_customer(999) is None

    def test_get_all_customers_sorted_by_name(self, db):
        for name in ["Zdenek", "Adam", "Marek"]:
            db.add_customer(name, "blue")

        assert [c.name for c in db.get_all_customers()] == ["Adam", "Marek", "Zdenek"]

    def test_returns_dtos_not_orm_objects(self, db):
        db.add_customer("Marek", "blue")
        assert isinstance(db.get_all_customers()[0], CustomerDTO)

    def test_update_customer_both_fields(self, db):
        db.add_customer("Marek", "blue")
        cid = db.get_all_customers()[0].id

        db.update_customer(cid, name="Marek Raška", color="green")

        assert db.get_customer(cid) == CustomerDTO(cid, "Marek Raška", "green")

    def test_update_customer_only_given_fields(self, db):
        db.add_customer("Marek", "blue")
        cid = db.get_all_customers()[0].id

        db.update_customer(cid, color="green")

        customer = db.get_customer(cid)
        assert customer.name == "Marek"
        assert customer.color == "green"

    def test_update_missing_customer_does_nothing(self, db):
        db.update_customer(999, name="Nobody")  # must not raise
        assert db.get_all_customers() == []

    def test_remove_customer(self, db):
        db.add_customer("Marek", "blue")
        cid = db.get_all_customers()[0].id

        assert db.remove_customer(cid) is True
        assert db.get_customer(cid) is None

    def test_remove_missing_customer_returns_false(self, db):
        assert db.remove_customer(999) is False

    def test_remove_customer_deletes_their_orders(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
        db.upsert_order(ids["Petr"], ids["PZ1"], today, 1)

        db.remove_customer(ids["Marek"])

        assert [e.customer.name for e in db.orders_on(today)] == ["Petr"]

# endregion


# region MENU ITEM

class TestMenuItems:
    def test_add_and_list_menu_items_sorted_by_code(self, db):
        db.add_menu_item("PZ1", "Margherita")
        db.add_menu_item("BG2", "Burger")

        items = db.get_all_menu_items()
        assert [(i.code, i.name) for i in items] == [("BG2", "Burger"), ("PZ1", "Margherita")]

    def test_duplicate_code_is_rejected(self, db):
        db.add_menu_item("PZ1", "Margherita")

        with pytest.raises(IntegrityError):
            db.add_menu_item("PZ1", "Another pizza")

        assert len(db.get_all_menu_items()) == 1

    def test_update_menu_item_name(self, db):
        db.add_menu_item("PZ1", "Margherita")
        item_id = db.get_all_menu_items()[0].id

        db.update_menu_item(item_id, name="Pizza Margherita")

        assert db.get_all_menu_items()[0].name == "Pizza Margherita"

    def test_update_menu_item_without_name_keeps_it(self, db):
        db.add_menu_item("PZ1", "Margherita")
        item_id = db.get_all_menu_items()[0].id

        db.update_menu_item(item_id)

        assert db.get_all_menu_items()[0].name == "Margherita"

    def test_remove_menu_item(self, db):
        db.add_menu_item("PZ1", "Margherita")
        item_id = db.get_all_menu_items()[0].id

        assert db.remove_menu_item(item_id) is True
        assert db.get_all_menu_items() == []

    def test_remove_missing_menu_item_returns_false(self, db):
        assert db.remove_menu_item(999) is False

    def test_cannot_remove_menu_item_with_orders(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

        with pytest.raises(IntegrityError):
            db.remove_menu_item(ids["PZ1"])

        # item and order are both still there
        assert "PZ1" in [i.code for i in db.get_all_menu_items()]
        assert db.totals_on(today) == [("PZ1", 2)]

# endregion


# region ORDER

class TestUpsertOrder:
    def test_insert_new_order(self, populated, today):
        db, ids = populated

        order = db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

        assert isinstance(order, OrderDTO)
        assert order.menu_item_code == "PZ1"
        assert order.count == 2
        assert order.date == today

    def test_update_existing_order_replaces_count(self, populated, today):
        db, ids = populated
        first = db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

        second = db.upsert_order(ids["Marek"], ids["PZ1"], today, 5)

        assert second.id == first.id  # same row, not a new one
        assert second.count == 5
        assert db.totals_on(today) == [("PZ1", 5)]

    def test_count_zero_deletes_existing_order(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

        assert db.upsert_order(ids["Marek"], ids["PZ1"], today, 0) is None
        assert db.orders_on(today) == []

    def test_count_zero_for_missing_order_does_nothing(self, populated, today):
        db, ids = populated

        assert db.upsert_order(ids["Marek"], ids["PZ1"], today, 0) is None
        assert db.orders_on(today) == []

    def test_negative_count_raises(self, populated, today):
        db, ids = populated

        with pytest.raises(ValueError):
            db.upsert_order(ids["Marek"], ids["PZ1"], today, -1)

    def test_different_dates_are_separate_orders(self, populated, today):
        db, ids = populated
        tomorrow = today + datetime.timedelta(days=1)

        a = db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
        b = db.upsert_order(ids["Marek"], ids["PZ1"], tomorrow, 3)

        assert a.id != b.id
        assert db.totals_on(today) == [("PZ1", 2)]
        assert db.totals_on(tomorrow) == [("PZ1", 3)]

    def test_unknown_customer_is_rejected(self, populated, today):
        """Also verifies that PRAGMA foreign_keys=ON is actually active."""
        db, ids = populated

        with pytest.raises(IntegrityError):
            db.upsert_order(999, ids["PZ1"], today, 1)

    def test_unknown_menu_item_is_rejected(self, populated, today):
        db, ids = populated

        with pytest.raises(IntegrityError):
            db.upsert_order(ids["Marek"], 999, today, 1)

    def test_date_round_trips_as_date_object(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 1)

        order = db.orders_on(today)[0].orders[0]
        assert type(order.date) is datetime.date

# endregion


# region REPORTS

class TestOrdersOn:
    def test_no_orders(self, populated, today):
        db, _ = populated
        assert db.orders_on(today) == []

    def test_groups_orders_by_customer(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
        db.upsert_order(ids["Marek"], ids["BG2"], today, 1)
        db.upsert_order(ids["Petr"], ids["PZ1"], today, 3)

        result = db.orders_on(today)

        assert all(isinstance(e, CustomerOrdersDTO) for e in result)
        # customers sorted by name, items sorted by code
        assert [
            (e.customer.name, [(o.menu_item_code, o.count) for o in e.orders])
            for e in result
        ] == [
            ("Marek", [("BG2", 1), ("PZ1", 2)]),
            ("Petr", [("PZ1", 3)]),
        ]

    def test_excludes_customers_without_orders_that_day(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

        assert [e.customer.name for e in db.orders_on(today)] == ["Marek"]

    def test_excludes_other_dates(self, populated, today):
        db, ids = populated
        yesterday = today - datetime.timedelta(days=1)
        db.upsert_order(ids["Marek"], ids["PZ1"], yesterday, 5)
        db.upsert_order(ids["Marek"], ids["BG2"], today, 1)

        [entry] = db.orders_on(today)
        assert [(o.menu_item_code, o.count) for o in entry.orders] == [("BG2", 1)]

    def test_customers_with_same_name_are_not_merged(self, db, today):
        db.add_customer("Marek", "blue")
        db.add_customer("Marek", "red")
        db.add_menu_item("PZ1", "Margherita")
        item_id = db.get_all_menu_items()[0].id
        for c in db.get_all_customers():
            db.upsert_order(c.id, item_id, today, 1)

        result = db.orders_on(today)

        assert len(result) == 2
        assert {e.customer.color for e in result} == {"blue", "red"}


class TestTotalsOn:
    def test_no_orders(self, populated, today):
        db, _ = populated
        assert db.totals_on(today) == []

    def test_sums_across_customers(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
        db.upsert_order(ids["Petr"], ids["PZ1"], today, 3)
        db.upsert_order(ids["Petr"], ids["BG2"], today, 1)

        assert db.totals_on(today) == [("BG2", 1), ("PZ1", 5)]

    def test_ignores_other_dates(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
        db.upsert_order(ids["Marek"], ids["PZ1"], today + datetime.timedelta(days=1), 10)

        assert db.totals_on(today) == [("PZ1", 2)]

    def test_items_without_orders_are_omitted(self, populated, today):
        db, ids = populated
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

        assert [code for code, _ in db.totals_on(today)] == ["PZ1"]


class TestOrdersOfCustomer:
    def test_no_orders(self, populated):
        db, ids = populated
        assert db.orders_of_customer(ids["Marek"]) == []

    def test_returns_only_that_customers_orders_sorted(self, populated, today):
        db, ids = populated
        tomorrow = today + datetime.timedelta(days=1)
        db.upsert_order(ids["Marek"], ids["PZ1"], tomorrow, 1)
        db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
        db.upsert_order(ids["Marek"], ids["BG2"], today, 3)
        db.upsert_order(ids["Petr"], ids["PZ1"], today, 9)

        orders = db.orders_of_customer(ids["Marek"])

        assert [(o.date, o.menu_item_code, o.count) for o in orders] == [
            (today, "BG2", 3),
            (today, "PZ1", 2),
            (tomorrow, "PZ1", 1),
        ]

# endregion
