# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"U Buriana" is a small Flask app for managing daily food orders: customers (each with a display color) order menu items (short codes like `P1`, `H1`) per date. The app shows a per-day cooking summary (total count per menu item) and is meant to print color-striped delivery labels as a PDF. Sample/test data uses Czech surnames and dates in late 2026.

## Environment & commands

Python venv lives in `.venv/` (Windows). There is no requirements file; installed deps are Flask 3.1, SQLAlchemy 2.0, reportlab 5.0, pytest 9.

```powershell
.venv\Scripts\python -m pytest tests                              # all tests (VS Code is configured for pytest on tests/)
.venv\Scripts\python -m pytest tests/test_database.py::test_name   # single test
.venv\Scripts\python -m flask --app main run --debug               # run web app
.venv\Scripts\python -m model.database                             # in-memory smoke test of DBManager
```

Run everything from the repo root: imports are root-relative (`from model.database import DBManager`) and several scripts open paths relative to CWD (`tests/test_data/*.csv`, `colors.txt`).

## Architecture

- **`model/models.py`** — SQLAlchemy 2.0 declarative models: `Customer`, `MenuItem`, `Order`. `Order` is one row per (customer, menu_item, date), enforced by a unique constraint, with a `count > 0` check constraint. Deleting a customer cascades to its orders. Deleting a menu item that still has orders fails with `IntegrityError`, because foreign keys are enforced.
- **`model/helpers.py`** — frozen dataclass DTOs (`CustomerDTO`, `OrderDTO`, `MenuItemDTO`, `CustomerOrdersDTO`) with `from_orm` constructors. ORM objects never leave a session; everything returned from `DBManager` is a DTO.
- **`model/database.py`** — `DBManager` is the only data access layer. Each method opens its own short-lived `Session(self.engine)`. The constructor takes the SQLite path (default `database.db` in CWD, `":memory:"` for tests), turns on `PRAGMA foreign_keys=ON` through a connect event, and calls `create_all`. Key semantics:
  - `upsert_order(..., count)`: `count == 0` deletes the order, a negative count raises `ValueError`, otherwise it inserts or updates.
  - `orders_on(date)` returns orders grouped per customer as `CustomerOrdersDTO`. `totals_on(date)` returns `[(menu_code, total)]` for the cooking summary.
- **`main.py`** — Flask routes that render `templates/*.html` with data from a module-level `DBManager`. `/customers/<id>` shows an editable customer and order grid. There are separate POST routes: `/customers/<id>` for name and color, `/customers/<id>/orders` for the grid (inputs named `count:<iso date>:<menu item id>`), `/customers/<id>/delete` to delete, and `/customers/new` to create a placeholder customer and redirect to its page. `/api/delivery_labels?date=` returns the label PDF inline. `/api/order_summary` is a stub.
- **`utils/PDFRender/PDFGenerator.py`** — `PDFLabels` uses reportlab to lay out a grid of labels on A4 (default 16×4), each with a customer color stripe, name, and item codes. `delivery_labels_pdf(orders_on(date))` builds one label per customer in memory. Labels fill from the top-left and continue on new pages. It uses Arial from the Windows fonts when available, because Helvetica can't draw Czech letters. The script's `main()` still reads a `colors.txt` that doesn't exist in the repo.
- **`tests/`** — `conftest.py` provides the fixtures: `db` (a fresh `DBManager(":memory:")`), `today` (a fixed date), and `populated`. `populated` returns `(db, ids)`, a DB with customers Marek and Petr and menu items PZ1 and BG2, where `ids` maps each name or code to its id. `test_database.py` tests `DBManager` by class (customers, menu items, upsert, reports). `pytest.ini` puts the repo root on `pythonpath`, so a plain `pytest` works too. `temp/` holds throwaway scripts that generate sample data from `tests/test_data/*.csv`.

## Known incomplete state

This is early work in progress. Several pieces are broken. Check them before assuming something works:
- `/` works. `DBManager.populate_sample()` is a stub. `database.db` has hand-seeded sample data: menu items P1/P2/H1/H2, a few customers, and orders for 2026-09-24 and 2026-09-25.
- `ORDER BY Customer.name` uses SQLite's binary collation, so names starting with accented letters (e.g. `Černý`) sort after `z`.
- The repo is not a git repository.
