from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify
)

from database import (
    db,
    Product,
    Order,
    OrderItem,
    ExceptionRecord
)

from decision_engine import (
    allocate_inventory,
    check_stock_alerts,
    get_bottleneck
)

from datetime import datetime


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///warehouse.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

with app.app_context():

    db.create_all()

    # Add sample products only once
    if Product.query.count() == 0:

        products = [

            Product(
                sku="WM-1001",
                name="Wireless Mouse",
                category="Accessories",
                quantity=7,
                reorder_level=10,
                reorder_quantity=30,
                location="A-01"
            ),

            Product(
                sku="KB-2001",
                name="Gaming Keyboard",
                category="Accessories",
                quantity=15,
                reorder_level=8,
                reorder_quantity=20,
                location="A-02"
            ),

            Product(
                sku="HC-3001",
                name="HDMI Cable",
                category="Cables",
                quantity=3,
                reorder_level=5,
                reorder_quantity=25,
                location="B-01"
            ),

            Product(
                sku="UC-4001",
                name="USB-C Adapter",
                category="Adapters",
                quantity=2,
                reorder_level=5,
                reorder_quantity=25,
                location="B-02"
            ),

            Product(
                sku="LS-5001",
                name="Laptop Stand",
                category="Office",
                quantity=20,
                reorder_level=6,
                reorder_quantity=15,
                location="C-01"
            )
        ]

        db.session.add_all(products)
        db.session.commit()


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():

    total_products = Product.query.count()

    total_orders = Order.query.count()

    pending_orders = Order.query.filter(
        Order.status != "Dispatched"
    ).count()

    low_stock = Product.query.filter(
        Product.quantity <= Product.reorder_level
    ).count()

    dispatched = Order.query.filter_by(
        status="Dispatched"
    ).count()

    bottleneck = get_bottleneck()

    recent_orders = Order.query.order_by(
        Order.created_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        low_stock=low_stock,
        dispatched=dispatched,
        bottleneck=bottleneck,
        recent_orders=recent_orders
    )


# --------------------------------------------------
# INVENTORY
# --------------------------------------------------

@app.route("/inventory")
def inventory():

    products = Product.query.order_by(
        Product.quantity.asc()
    ).all()

    alerts = check_stock_alerts()

    return render_template(
        "inventory.html",
        products=products,
        alerts=alerts
    )


# --------------------------------------------------
# ADD PRODUCT
# --------------------------------------------------

@app.route(
    "/inventory/add",
    methods=["POST"]
)
def add_product():

    product = Product(

        sku=request.form["sku"],

        name=request.form["name"],

        category=request.form["category"],

        quantity=int(
            request.form["quantity"]
        ),

        reorder_level=int(
            request.form["reorder_level"]
        ),

        reorder_quantity=int(
            request.form["reorder_quantity"]
        ),

        location=request.form["location"]
    )

    db.session.add(product)

    db.session.commit()

    return redirect(
        url_for("inventory")
    )


# --------------------------------------------------
# CREATE ORDER
# --------------------------------------------------

@app.route(
    "/orders",
    methods=["GET", "POST"]
)
def orders():

    if request.method == "POST":

        product_id = int(
            request.form["product_id"]
        )

        quantity = int(
            request.form["quantity"]
        )

        priority = request.form["priority"]

        order_count = Order.query.count() + 1

        order = Order(

            order_number=
                f"ORD-{1000 + order_count}",

            customer=request.form["customer"],

            priority=priority,

            status="Pending",

            total_amount=float(
                request.form["amount"]
            )
        )

        db.session.add(order)

        db.session.commit()

        item = OrderItem(

            order_id=order.id,

            product_id=product_id,

            quantity=quantity
        )

        db.session.add(item)

        db.session.commit()

        # Automatically allocate inventory
        allocate_inventory(order)

        # Check whether allocation succeeded
        item = OrderItem.query.filter_by(
            order_id=order.id
        ).first()

        if item.allocated_quantity == item.quantity:

            order.status = "Allocated"

        elif item.allocated_quantity > 0:

            order.status = "Partially Allocated"

            exception = ExceptionRecord(

                order_id=order.id,

                exception_type="Partial Allocation",

                description=
                "Order could not be fully allocated because inventory was insufficient.",

                status="Open"
            )

            db.session.add(exception)

        else:

            order.status = "Stockout"

            exception = ExceptionRecord(

                order_id=order.id,

                exception_type="Out of Stock",

                description=
                "Required product is currently unavailable.",

                status="Open"
            )

            db.session.add(exception)

        db.session.commit()

        return redirect(
            url_for("orders")
        )

    all_orders = Order.query.order_by(
        Order.created_at.desc()
    ).all()

    products = Product.query.all()

    return render_template(
        "orders.html",
        orders=all_orders,
        products=products
    )


# --------------------------------------------------
# PICKING
# --------------------------------------------------

@app.route("/picking")
def picking():

    orders = Order.query.filter(
        Order.status.in_([
            "Allocated",
            "Partially Allocated",
            "Picking"
        ])
    ).order_by(
        Order.priority.desc()
    ).all()

    return render_template(
        "picking.html",
        orders=orders
    )


@app.route(
    "/picking/<int:order_id>",
    methods=["POST"]
)
def start_picking(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    order.status = "Picking"

    db.session.commit()

    return redirect(
        url_for("picking")
    )


# --------------------------------------------------
# PACKING
# --------------------------------------------------

@app.route(
    "/packing/<int:order_id>",
    methods=["POST"]
)
def packing(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    order.status = "Packing"

    db.session.commit()

    return redirect(
        url_for("dashboard")
    )


# --------------------------------------------------
# QUALITY CHECK
# --------------------------------------------------

@app.route(
    "/quality/<int:order_id>",
    methods=["POST"]
)
def quality_check(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    result = request.form.get(
        "result"
    )

    if result == "pass":

        order.status = "Dispatch Ready"

    else:

        order.status = "Quality Hold"

        exception = ExceptionRecord(

            order_id=order.id,

            exception_type="Quality Failure",

            description=
            "Order failed quality inspection.",

            status="Open"
        )

        db.session.add(exception)

    db.session.commit()

    return redirect(
        url_for("dashboard")
    )


# --------------------------------------------------
# DISPATCH
# --------------------------------------------------

@app.route("/dispatch")
def dispatch():

    orders = Order.query.filter(
        Order.status.in_([
            "Dispatch Ready",
            "Dispatched"
        ])
    ).order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "dispatch.html",
        orders=orders
    )


@app.route(
    "/dispatch/<int:order_id>",
    methods=["POST"]
)
def dispatch_order(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    order.status = "Dispatched"

    db.session.commit()

    return redirect(
        url_for("dispatch")
    )


# --------------------------------------------------
# EXCEPTIONS
# --------------------------------------------------

@app.route("/exceptions")
def exceptions():

    records = ExceptionRecord.query.order_by(
        ExceptionRecord.created_at.desc()
    ).all()

    return render_template(
        "exceptions.html",
        exceptions=records
    )


@app.route(
    "/exceptions/<int:id>/resolve",
    methods=["POST"]
)
def resolve_exception(id):

    record = ExceptionRecord.query.get_or_404(
        id
    )

    record.status = "Resolved"

    record.resolution = request.form.get(
        "resolution",
        "Issue resolved by warehouse operator."
    )

    db.session.commit()

    return redirect(
        url_for("exceptions")
    )


# --------------------------------------------------
# ANALYTICS API
# --------------------------------------------------

@app.route("/api/analytics")
def analytics():

    return jsonify({

        "orders": Order.query.count(),

        "pending": Order.query.filter(
            Order.status != "Dispatched"
        ).count(),

        "dispatched": Order.query.filter_by(
            status="Dispatched"
        ).count(),

        "low_stock": Product.query.filter(
            Product.quantity <= Product.reorder_level
        ).count(),

        "exceptions": ExceptionRecord.query.filter_by(
            status="Open"
        ).count(),

        "bottleneck": get_bottleneck()

    })


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )