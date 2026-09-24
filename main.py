from flask import Flask, request, abort, redirect, url_for, send_file
from flask import render_template
from model.database import DBManager
from model.helpers import CustomerDTO, OrderDTO, MenuItemDTO
from utils.PDFRender.PDFGenerator import delivery_labels_pdf
import datetime
import io

DEBUG = True

db = DBManager()
if DEBUG: 
    db.populate_sample()


app = Flask(__name__)

@app.route("/")
def index():
    today = datetime.date.today()

    customers = db.get_all_customers()
    cooking_summary = db.totals_on(today)
    orders = db.orders_on(today)

    return render_template("index.html", 
        selected_date = today,
        cooking_summary = cooking_summary,
        customers = customers
    )


ORDER_DAYS_AHEAD = 14
NEW_CUSTOMER_NAME = "New customer"
NEW_CUSTOMER_COLOR = "gray"

@app.post("/customers/new")
def new_customer():
    customer_id = db.add_customer(NEW_CUSTOMER_NAME, NEW_CUSTOMER_COLOR)
    return redirect(url_for("customer_page", customer_id=customer_id))


@app.get("/customers/<int:customer_id>")
def customer_page(customer_id:int):
    customer = db.get_customer(customer_id)
    if customer is None:
        abort(404)

    today = datetime.date.today()
    menu_items = db.get_all_menu_items()
    orders = db.orders_of_customer(customer_id)
    counts = {(o.date, o.menu_item_code): o.count for o in orders}

    upcoming = {today + datetime.timedelta(days=i) for i in range(ORDER_DAYS_AHEAD)}
    dates = sorted({d for d, _ in counts} | upcoming)
    rows = [(d, [counts.get((d, m.code), 0) for m in menu_items]) for d in dates]

    return render_template("customer.html",
        customer = customer,
        menu_items = menu_items,
        rows = rows,
        today = today,
        order_count = len(orders)
    )


@app.post("/customers/<int:customer_id>")
def save_customer(customer_id:int):
    if db.get_customer(customer_id) is None:
        abort(404)

    name = request.form.get("name", "").strip()
    color = request.form.get("color", "").strip()
    db.update_customer(customer_id, name or None, color or None)

    return redirect(url_for("customer_page", customer_id=customer_id))


@app.post("/customers/<int:customer_id>/orders")
def save_orders(customer_id:int):
    if db.get_customer(customer_id) is None:
        abort(404)

    # order inputs are named "count:<iso date>:<menu item id>"
    for key, value in request.form.items():
        if not key.startswith("count:"):
            continue
        try:
            _, date_str, item_str = key.split(":")
            item_id = int(item_str)
            date = datetime.date.fromisoformat(date_str)
            count = int(value) if value.strip() else 0
        except ValueError:
            continue
        if count < 0:
            continue
        db.upsert_order(customer_id, item_id, date, count)

    return redirect(url_for("customer_page", customer_id=customer_id))


@app.post("/customers/<int:customer_id>/delete")
def delete_customer(customer_id:int):
    # orders are removed by cascade
    if not db.remove_customer(customer_id):
        abort(404)

    return redirect(url_for("index"))



########################## API ###############################
@app.get("/api/order_summary")
def order_summary( date:datetime.date ):
    ...

@app.get("/api/delivery_labels")
def delivery_labels():
    date_str = request.args.get("date")
    try:
        date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    except ValueError:
        abort(400)

    pdf = delivery_labels_pdf(db.orders_on(date))

    return send_file(io.BytesIO(pdf),
        mimetype = "application/pdf",
        download_name = f"labels-{date.isoformat()}.pdf"
    )

