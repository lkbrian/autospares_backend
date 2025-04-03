# models.py
from datetime import datetime
from config import db
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Address(db.Model, SerializerMixin):
    __tablename__ = "addresses"
    serialize_only = (
        "id",
        "customer_id",
        "specific_address",
        "area_town",
        "county",
        "city_town",
        "created_at",
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    specific_address = db.Column(
        db.Text, nullable=False
    )  # Renamed address_line to specific_address
    county = db.Column(db.Text, nullable=False)
    area_town = db.Column(db.Text, nullable=False)  # Renamed town to area_town
    city_town = db.Column(
        db.Text, nullable=False
    )  # Added city_town as per new requirements
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shipping_orders = db.relationship(
        "Order", foreign_keys="Order.shipping_address_id", backref="shipping_address"
    )
    billing_orders = db.relationship(
        "Order", foreign_keys="Order.billing_address_id", backref="billing_address"
    )


class Category(db.Model, SerializerMixin):
    __tablename__ = "categories"
    serialize_only = (
        "id",
        "name",
        "slug",
        "description",
        "parent_id",
        "created_at",
        "image_url",
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.Text)

    parent = db.relationship("Category", remote_side=[id], backref="subcategories")
    products = db.relationship("Product", backref="category")


class Brand(db.Model, SerializerMixin):
    __tablename__ = "brands"
    serialize_only = (
        "id",
        "name",
        "slug",
        "description",
        "logo_url",
        "website",
        "created_at",
        "country_of_origin",
        "year_established",
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.Text)
    website = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    country_of_origin = db.Column(db.Text)
    year_established = db.Column(db.Integer)

    products = db.relationship("Product", backref="brand")


class Product(db.Model, SerializerMixin):
    __tablename__ = "products"
    serialize_only = (
        "id",
        "name",
        "sku",
        "description",
        "imgUrl",
        "price",
        "cost",
        "discount",
        "category_id",
        "brand_id",
        "stock",
        "weight",
        "dimensions",
        "features",
        "specifications",
        "status",
        "meta_title",
        "meta_description",
        "is_featured",
        "compatible_makes",
        "compatible_models",
    )

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.Text, nullable=False)
    sku = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    imgUrl = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float)
    discount = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"))
    stock = db.Column(db.Integer, nullable=False, default=1)
    weight = db.Column(db.Float)
    dimensions = db.Column(db.Text)  # Store as JSON string
    features = db.Column(db.Text)
    specifications = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, default="Active")
    meta_title = db.Column(db.Text)
    meta_description = db.Column(db.Text)
    is_featured = db.Column(db.Boolean, default=False)
    compatible_makes = db.Column(db.Text)  # Store as JSON string
    compatible_models = db.Column(db.Text)  # Store as JSON string

    images = db.relationship("ProductImage", backref="product")
    order_items = db.relationship("OrderItem", backref="product")
    reviews = db.relationship("Review", backref="product")
    inventory_logs = db.relationship("InventoryLog", backref="product")


class ProductImage(db.Model, SerializerMixin):
    __tablename__ = "product_images"
    serialize_only = ("id", "product_id", "url", "created_at", "is_primary", "alt_text")

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    url = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_primary = db.Column(db.Boolean, default=False)
    alt_text = db.Column(db.Text)


class Customer(db.Model, SerializerMixin):
    __tablename__ = "customers"
    serialize_only = (
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "created_at",
        "user_id",
    )

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    phone = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Text)

    addresses = db.relationship("Address", backref="customer")
    orders = db.relationship("Order", backref="customer")
    reviews = db.relationship("Review", backref="customer")


class Order(db.Model, SerializerMixin):
    __tablename__ = "orders"
    serialize_only = (
        "id",
        "customer_id",
        "order_number",
        "status",
        "total_amount",
        "shipping_address_id",
        "billing_address_id",
        "payment_method",
        "payment_status",
        "shipping_method",
        "shipping_cost",
        "tax_amount",
        "discount_amount",
        "notes",
        "delivery_company",
        "tracking_number",
        "delivery_person",
        "estimated_delivery_date",
        "created_at",
        "updated_at",
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    order_number = db.Column(db.Text, unique=True, nullable=False)
    status = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    shipping_address_id = db.Column(
        db.Integer, db.ForeignKey("addresses.id"), nullable=False
    )
    billing_address_id = db.Column(db.Integer, db.ForeignKey("addresses.id"))
    shipping_cost = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.Text, nullable=False, default="mpesa")
    payment_status = db.Column(db.Text, nullable=False)
    discount_amount = db.Column(db.Text)
    shipping_method = db.Column(db.Text)
    tax_amount = db.Column(db.Text)
    notes = db.Column(db.Text)
    delivery_company = db.Column(db.Text)
    tracking_number = db.Column(db.Text)
    delivery_person = db.Column(db.Text)
    estimated_delivery_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items = db.relationship("OrderItem", backref="order")


class OrderItem(db.Model, SerializerMixin):
    __tablename__ = "order_items"
    serialize_only = (
        "id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "total_price",
        "created_at",
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model, SerializerMixin):
    __tablename__ = "reviews"
    serialize_only = (
        "id",
        "product_id",
        "customer_id",
        "rating",
        "comment",
        "created_at",
        "is_approved",
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)


class InventoryLog(db.Model, SerializerMixin):
    __tablename__ = "inventory_logs"
    serialize_only = (
        "id",
        "product_id",
        "quantity_change",
        "previous_stock",
        "new_stock",
        "change_type",
        "reference_id",
        "notes",
        "created_at",
        "created_by",
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    change_type = db.Column(db.Text, nullable=False)
    reference_id = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))


class Role(db.Model, SerializerMixin):
    __tablename__ = "roles"
    serialize_only = ("id", "name", "level")
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    level = db.Column(db.Integer, nullable=False)

    # Relationship to users
    users = db.relationship("User", backref="role")


class User(db.Model, SerializerMixin):
    __tablename__ = "users"

    serialize_only = (
        "id",
        "email",
        "first_name",
        "last_name",
        "created_at",
        "last_login",
        "is_active",
        "role.name",  # Serialize role name instead of role_id
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Foreign key relationship with roles
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
