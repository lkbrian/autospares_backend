from flask import Blueprint
from flask_restful import Api
from resources import (  # Import your resource classes
    AddressResource,
    BrandResource,
    CategoryResource,
    CustomerResource,
    InventoryLogResource,
    LoginUser,
    LogoutUser,
    OrderItemResource,
    OrderProcess,
    OrderResource,
    ProductResource,
    ProductRoute,
    RegisterUser,
    ReviewResource,
    RoleResource,
    UserResource,
)

# Create a Blueprint for API v1
api_v1_blueprint = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api = Api(api_v1_blueprint)

# Register resources with Flask-RESTful API

# Auth
api.add_resource(RegisterUser, "/register")
api.add_resource(LoginUser, "/login")
api.add_resource(LogoutUser, "/logout")

# categories
api.add_resource(CategoryResource, "/categories", "/category/<int:id>")

# brands
api.add_resource(BrandResource, "/brands", "/brands/<int:id>")

# products
api.add_resource(ProductResource, "/products", "/product/<int:id>")
api.add_resource(ProductRoute, "/create-product")
# api.add_resource(ProductResource, "/getAll")

# customers
api.add_resource(CustomerResource, "/customers", "/customer/<int:id>")

# addresses
api.add_resource(AddressResource, "/addresses", "/addresses/<int:id>")

# orders
api.add_resource(OrderResource, "/orders", "/order/<int:id>")
api.add_resource(OrderItemResource, "/order_items", "/order_item/<int:id>")
api.add_resource(OrderProcess, "/create-order/process")

# roles
api.add_resource(RoleResource, "/roles", "/role/<int:id>")

# users
api.add_resource(UserResource, "/users", "/users/<int:id>")

# reviews
api.add_resource(ReviewResource, "/reviews", "/reviews/<int:id>")

# inventory
api.add_resource(InventoryLogResource, "/inventory_logs", "/inventory_logs/<int:id>")
