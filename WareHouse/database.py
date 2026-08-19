from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)

    category = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=0)

    reorder_level = db.Column(db.Integer, default=10)
    reorder_quantity = db.Column(db.Integer, default=20)

    location = db.Column(db.String(50))

    damaged = db.Column(db.Integer, default=0)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    customer = db.Column(db.String(150))

    priority = db.Column(
        db.String(30),
        default="Low"
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    total_amount = db.Column(
        db.Float,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("order.id")
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id")
    )

    quantity = db.Column(db.Integer)

    allocated_quantity = db.Column(
        db.Integer,
        default=0
    )


class ExceptionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        nullable=True
    )

    exception_type = db.Column(
        db.String(100)
    )

    description = db.Column(
        db.String(500)
    )

    status = db.Column(
        db.String(50),
        default="Open"
    )

    resolution = db.Column(
        db.String(500),
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )