import datetime

import pytest

import main


@pytest.fixture
def client(populated, monkeypatch):
    db, ids = populated
    monkeypatch.setattr(main, "db", db)
    return main.app.test_client(), db, ids


def test_customer_page_shows_name_and_zero_grid(client):
    c, db, ids = client
    response = c.get(f"/customers/{ids['Marek']}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Marek" in html
    assert "PZ1" in html and "BG2" in html
    assert 'value="0"' in html


def test_customer_page_shows_existing_order(client):
    c, db, ids = client
    today = datetime.date.today()
    db.upsert_order(ids["Marek"], ids["PZ1"], today, 4)

    html = c.get(f"/customers/{ids['Marek']}").get_data(as_text=True)

    assert f'name="count:{today.isoformat()}:{ids["PZ1"]}"' in html
    assert 'value="4"' in html


def test_unknown_customer_is_404(client):
    c, _, _ = client
    assert c.get("/customers/999").status_code == 404
    assert c.post("/customers/999").status_code == 404


def test_save_customer_updates_name_and_color_only(client):
    c, db, ids = client
    key = f"count:{datetime.date.today().isoformat()}:{ids['PZ1']}"

    response = c.post(f"/customers/{ids['Marek']}",
                      data={"name": "Marek R", "color": "#00ff00", key: "3"})

    assert response.status_code == 302
    customer = db.get_customer(ids["Marek"])
    assert (customer.name, customer.color) == ("Marek R", "#00ff00")
    assert db.orders_of_customer(ids["Marek"]) == []


def test_save_orders_creates_and_deletes_orders(client):
    c, db, ids = client
    key = f"count:{datetime.date.today().isoformat()}:{ids['PZ1']}"

    response = c.post(f"/customers/{ids['Marek']}/orders", data={key: "3"})

    assert response.status_code == 302
    assert [(o.menu_item_code, o.count) for o in db.orders_of_customer(ids["Marek"])] == [("PZ1", 3)]
    assert db.get_customer(ids["Marek"]).name == "Marek"

    c.post(f"/customers/{ids['Marek']}/orders", data={key: "0"})
    assert db.orders_of_customer(ids["Marek"]) == []


def test_save_orders_ignores_invalid_counts(client):
    c, db, ids = client
    today = datetime.date.today().isoformat()

    c.post(f"/customers/{ids['Marek']}/orders", data={
        f"count:{today}:{ids['PZ1']}": "-2",
        f"count:{today}:{ids['BG2']}": "abc",
        "count:not-a-date:1": "5",
    })

    assert db.orders_of_customer(ids["Marek"]) == []


def test_save_orders_unknown_customer_is_404(client):
    c, _, _ = client
    assert c.post("/customers/999/orders").status_code == 404


def test_new_customer_creates_placeholder_and_redirects(client):
    c, db, _ = client

    response = c.post("/customers/new")

    assert response.status_code == 302
    created = [x for x in db.get_all_customers() if x.name == main.NEW_CUSTOMER_NAME]
    assert len(created) == 1
    assert response.headers["Location"].endswith(f"/customers/{created[0].id}")


def test_delete_customer_removes_customer_and_orders(client):
    c, db, ids = client
    db.upsert_order(ids["Marek"], ids["PZ1"], datetime.date.today(), 2)

    response = c.post(f"/customers/{ids['Marek']}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert db.get_customer(ids["Marek"]) is None
    assert db.orders_of_customer(ids["Marek"]) == []


def test_delete_unknown_customer_is_404(client):
    c, _, _ = client
    assert c.post("/customers/999/delete").status_code == 404


def test_customer_page_asks_before_delete(client):
    c, db, ids = client
    db.upsert_order(ids["Marek"], ids["PZ1"], datetime.date.today(), 2)

    html = c.get(f"/customers/{ids['Marek']}").get_data(as_text=True)

    assert f'action="/customers/{ids["Marek"]}/delete"' in html
    assert "data-confirm=" in html and "všechny jeho objednávky (1)" in html


def test_delivery_labels_returns_pdf(client):
    c, db, ids = client
    today = datetime.date.today()
    db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)

    response = c.get(f"/api/delivery_labels?date={today.isoformat()}")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_delivery_labels_without_date_uses_today(client):
    c, _, _ = client
    response = c.get("/api/delivery_labels")
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


def test_delivery_labels_bad_date_is_400(client):
    c, _, _ = client
    assert c.get("/api/delivery_labels?date=nope").status_code == 400


def test_index_links_to_delivery_labels(client):
    c, _, _ = client
    html = c.get("/").get_data(as_text=True)
    assert "/api/delivery_labels?date=" in html


def test_new_menu_item_is_added(client):
    c, db, _ = client

    response = c.post("/menu_items/new", data={"code": " H1 ", "name": "Guláš"})

    assert response.status_code == 302
    assert ("H1", "Guláš") in [(i.code, i.name) for i in db.get_all_menu_items()]


def test_new_menu_item_without_name(client):
    c, db, _ = client
    c.post("/menu_items/new", data={"code": "H1", "name": ""})
    assert ("H1", None) in [(i.code, i.name) for i in db.get_all_menu_items()]


@pytest.mark.parametrize("code", ["", "   ", "X" * 11])
def test_new_menu_item_invalid_code_is_400(client, code):
    c, db, _ = client
    assert c.post("/menu_items/new", data={"code": code}).status_code == 400
    assert len(db.get_all_menu_items()) == 2


def test_new_menu_item_duplicate_code_shows_error(client):
    c, db, _ = client

    response = c.post("/menu_items/new", data={"code": "PZ1"}, follow_redirects=True)

    assert "Položka s tímto kódem už v jídelníčku je." in response.get_data(as_text=True)
    assert len(db.get_all_menu_items()) == 2


def test_delete_menu_item_removes_its_orders(client):
    c, db, ids = client
    today = datetime.date.today()
    db.upsert_order(ids["Marek"], ids["PZ1"], today, 2)
    db.upsert_order(ids["Petr"], ids["BG2"], today, 1)

    response = c.post(f"/menu_items/{ids['PZ1']}/delete")

    assert response.status_code == 302
    assert [i.code for i in db.get_all_menu_items()] == ["BG2"]
    assert db.totals_on(today) == [("BG2", 1)]


def test_delete_unknown_menu_item_is_404(client):
    c, _, _ = client
    assert c.post("/menu_items/999/delete").status_code == 404


def test_index_warns_before_deleting_menu_item_with_orders(client):
    c, db, ids = client
    db.upsert_order(ids["Marek"], ids["PZ1"], datetime.date.today(), 2)

    html = c.get("/").get_data(as_text=True)

    assert f'action="/menu_items/{ids["PZ1"]}/delete"' in html
    assert "Opravdu smazat položku „PZ1“? Smažou se i všechny její objednávky" in html
    assert "Opravdu smazat položku „BG2“?\"" in html   # no orders, no warning
