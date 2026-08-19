from database import Product, Order, OrderItem, db


PRIORITY_SCORE = {
    "Urgent": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1
}


def calculate_priority(order):
    """
    Automatically determines order priority.
    """

    if order.priority == "Urgent":
        return 4

    if order.priority == "High":
        return 3

    if order.priority == "Medium":
        return 2

    return 1


def allocate_inventory(order):

    items = OrderItem.query.filter_by(
        order_id=order.id
    ).all()

    allocation_result = []

    for item in items:

        product = Product.query.get(
            item.product_id
        )

        if not product:
            continue

        required = item.quantity
        available = product.quantity

        if available >= required:

            item.allocated_quantity = required

            product.quantity -= required

            allocation_result.append({
                "product": product.name,
                "required": required,
                "allocated": required,
                "status": "Fully Allocated"
            })

        elif available > 0:

            item.allocated_quantity = available

            product.quantity = 0

            allocation_result.append({
                "product": product.name,
                "required": required,
                "allocated": available,
                "status": "Partially Allocated"
            })

        else:

            item.allocated_quantity = 0

            allocation_result.append({
                "product": product.name,
                "required": required,
                "allocated": 0,
                "status": "Out of Stock"
            })

    db.session.commit()

    return allocation_result


def check_stock_alerts():

    products = Product.query.all()

    alerts = []

    for product in products:

        if product.quantity == 0:

            alerts.append({
                "product": product.name,
                "status": "OUT OF STOCK",
                "recommended_order":
                    product.reorder_quantity
            })

        elif product.quantity <= product.reorder_level:

            alerts.append({
                "product": product.name,
                "status": "LOW STOCK",
                "recommended_order":
                    product.reorder_quantity
            })

    return alerts


def get_bottleneck():

    """
    Simple bottleneck decision engine.
    In a real system this could use historical timestamps.
    """

    orders = Order.query.all()

    stages = {
        "Picking": 0,
        "Packing": 0,
        "Quality Check": 0,
        "Dispatch": 0
    }

    for order in orders:

        if order.status in stages:
            stages[order.status] += 1

    if not orders:
        return {
            "stage": "None",
            "count": 0
        }

    bottleneck = max(
        stages,
        key=stages.get
    )

    return {
        "stage": bottleneck,
        "count": stages[bottleneck]
    }