from datetime import datetime
from config import db  # Assuming db and app are imported from config

# Import the Role model (adjust the import path if necessary)
import uuid

# from flask import request, jsonify, make_response
# from sqlalchemy.exc import IntegrityError
# from datetime import datetime
from models import Customer, Address, Order, OrderItem, Product, Role

# Define the roles data
data = [
    {"name": "user", "level": 1},
    {"name": "manager", "level": 2},
    {"name": "admin", "level": 3},
    {"name": "super_admin", "level": 4},
]


def role_generator():
    for dataitem in data:
        # Check if the role already exists to avoid duplication
        existing_role = Role.query.filter_by(name=dataitem["name"]).first()
        if not existing_role:
            role = Role(name=dataitem["name"], level=dataitem["level"])
            db.session.add(role)
    db.session.commit()


# Execute the function with Flask app context
# with app.app_context():
# role_generator()


def str_to_bool(value):
    """Convert string values like 'true' or 'false' into real boolean"""
    if isinstance(value, bool):  # If it's already a boolean, return it
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")  # Convert string to boolean
    return False  # Default to False if None or invalid input


def generate_unique_order_number():
    """Generate a unique order number and check for uniqueness."""
    while True:
        order_number = f"ATS_{uuid.uuid4().hex[:6]}"  # Generate a random order number
        existing_order = Order.query.filter_by(order_number=order_number).first()

        if not existing_order:
            return order_number


def generate_unique_tracking_number():
    """Generate a unique order number and check for uniqueness."""
    while True:
        tracking_number = f"TN_{uuid.uuid4().hex[:6]}"  # Generate a random order number
        existing_order = Order.query.filter_by(tracking_number=tracking_number).first()

        if not existing_order:
            return tracking_number


def get_or_create_customer(data):
    """Check if customer exists by email, return existing or create a new one."""
    existing_customer = Customer.query.filter_by(email=data["email"]).first()

    if existing_customer:
        return existing_customer, False  # Return existing customer

    customer = Customer(
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        phone=data.get("phone"),
        user_id=data.get("user_id"),
    )
    db.session.add(customer)
    return customer, True  # Return new customer


def get_or_create_address(data, customer_id):
    """Ensure a valid, non-duplicate address is used for the customer."""
    existing_address = Address.query.filter_by(
        customer_id=customer_id,
        specific_address=data["specific_address"],
        county=data["county"],
        area_town=data["area_town"],
        city_town=data["city_town"],
    ).first()

    if existing_address:
        return existing_address, False  # Return existing address

    address = Address(
        customer_id=customer_id,
        specific_address=data["specific_address"],
        county=data["county"],
        area_town=data["area_town"],
        city_town=data["city_town"],
    )
    db.session.add(address)
    return address, True  # Return new address


def create_order(data, customer_id, address_id):
    """Create an order after validating dependencies."""
    order_number = generate_unique_order_number()
    tracking_number = generate_unique_tracking_number()
    estimated_delivery_date_str = data.get("estimated_delivery_date")
    if estimated_delivery_date_str:
        try:
            estimated_delivery_date = datetime.strptime(
                estimated_delivery_date_str, "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            estimated_delivery_date = datetime.strptime(
                estimated_delivery_date_str, "%Y-%m-%d"
            )
    else:
        estimated_delivery_date = None
    order = Order(
        customer_id=customer_id,
        order_number=order_number,
        status=data["status"],  # Accessing data from passed 'order' object
        total_amount=data["total_amount"],
        shipping_address_id=address_id,
        billing_address_id=address_id,
        payment_method=data["payment_method"],
        payment_status=data["payment_status"],
        shipping_method=data.get("shipping_method"),
        shipping_cost=data.get("shipping_cost"),
        tax_amount=data.get("tax_amount"),
        discount_amount=data.get("discount_amount"),
        notes=data.get("notes"),
        delivery_company=data.get("delivery_company"),
        tracking_number=tracking_number,
        delivery_person=data.get("delivery_person"),
        estimated_delivery_date=estimated_delivery_date,
    )

    db.session.add(order)
    return order


def create_order_items(items, order_id):
    """Add order items ensuring products exist."""
    for item_data in items:
        product = Product.query.get(item_data["product_id"])
        if not product:
            raise ValueError(f"Product ID {item_data['product_id']} not found.")

        if item_data["quantity"] <= 0:
            raise ValueError(
                f"Invalid quantity ({item_data['quantity']}) for Product ID {item_data['product_id']}."
            )

        order_item = OrderItem(
            order_id=order_id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"],
        )
        db.session.add(order_item)
