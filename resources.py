# routes/routes.py
import os
import uuid
from datetime import datetime
from functools import wraps
from sqlite3 import IntegrityError
from urllib.parse import urljoin

from flask import jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
)
from flask_restful import Resource
from werkzeug.utils import secure_filename

from config import app, blacklist, db
from models import (
    Address,
    Brand,
    Category,
    Customer,
    InventoryLog,
    Order,
    OrderItem,
    Product,
    ProductImage,
    Review,
    Role,
    User,
)
from utils import (
    create_order,
    create_order_items,
    get_or_create_address,
    get_or_create_customer,
    str_to_bool,
)


def authorised_route(required_role_name):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role_name = claims.get("role", "user")

            user_role = Role.query.filter_by(name=user_role_name).first()
            required_role = Role.query.filter_by(name=required_role_name).first()

            if not user_role or not required_role:
                return make_response(jsonify({"message": "Role not found"}), 404)

            # Compare levels (higher or equal level can access)
            if user_role.level < required_role.level:
                return make_response(
                    jsonify({"message": "Access denied insufficient permissions"}),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator


class RegisterUser(Resource):
    def post(self):
        data = request.get_json()
        try:
            email = data.get("email")
            password = data.get("password")
            confirm_password = data.get("confirm_password")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            role_name = data.get("role", "user")

            if not email or not password or not confirm_password:
                return {"message": "Missing required fields"}, 400

            if password != confirm_password:
                return {"message": "Passwords do not match"}, 400

            if User.query.filter_by(email=email).first():
                return {"message": "Email already exists"}, 400

            # Get or create role
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                return make_response(jsonify({"msg": "role not found"}), 404)

            # Create new user
            new_user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role_id=role.id,
                created_at=datetime.utcnow(),
                is_active=True,
            )
            new_user.set_password(password)

            # Save to database
            db.session.add(new_user)
            db.session.commit()

            return make_response(jsonify({"msg": "User created successfully"}), 201)
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig)
            return make_response(jsonify({"msg": f" {error_message}"}), 400)

        except Exception as e:
            db.session.rollback()
            error_msg = str(e).split("\n")[0]

            return make_response(jsonify({"msg": error_msg}), 400)


class RegisterUsingToken(Resource):
    def post(self, token):
        data = request.get_json()
        try:
            email = data.get("email")
            password = data.get("password")
            confirm_password = data.get("confirm_password")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            role_name = data.get("role", "user")

            if not email or not password or not confirm_password:
                return {"message": "Missing required fields"}, 400

            if password != confirm_password:
                return {"message": "Passwords do not match"}, 400

            if User.query.filter_by(email=email).first():
                return {"message": "Email already exists"}, 400

            # Get or create role
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                return make_response(jsonify({"msg": "role not found"}), 404)

            new_user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role_id=role.id,
                created_at=datetime.utcnow(),
                is_active=True,
            )
            new_user.set_password(password)

            # Save to database
            db.session.add(new_user)
            db.session.commit()

            return make_response(jsonify({"msg": "User created successfully"}), 201)
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig)
            return make_response(jsonify({"msg": f" {error_message}"}), 400)

        except Exception as e:
            db.session.rollback()
            error_msg = str(e).split("\n")[0]

            return make_response(jsonify({"msg": error_msg}), 400)


# API Resource: User Login
class LoginUser(Resource):
    def post(self):
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return {"message": "Invalid credentials"}, 401

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "email": user.email,
                "password_hash": user.password_hash,
                "role": user.role.name if user.role else "user",
            },
        )
        return {
            "msg": "Login successful",
            "access_token": str(access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role.name if user.role else "user",
            },
        }, 200


# API Resource: Logout (Blacklist the Token)
class LogoutUser(Resource):
    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]  # Get token identifier
        blacklist.add(jti)  # Blacklist the token
        return {"message": "Successfully logged out"}, 200


class CategoryResource(Resource):
    def get(self, id=None):
        if id is None:
            categories = [
                {
                    **c.to_dict(),
                    "subcategories": [sub.to_dict() for sub in c.subcategories],
                }
                for c in Category.query.filter_by(parent_id=None).all()
            ]
            return make_response(jsonify(categories), 200)
        else:
            category = Category.query.filter_by(id=id).first()
            if not category:
                return make_response(jsonify({"msg": "Category not found"}), 404)
            return make_response(jsonify(category.to_dict()), 200)

    def post(self):
        data = request.get_json()
        parent_id = data.get("parent_id")

        if parent_id:
            existing_category = Category.query.filter_by(id=parent_id).first()
            if not existing_category:
                return make_response(jsonify({"msg": "Parent category not found"}), 404)

        try:
            category = Category(
                name=data["name"],
                slug=data["slug"],
                description=data.get("description"),
                parent_id=existing_category.parent_id if parent_id else None,
                image_url=data.get("image_url"),
            )
            db.session.add(category)
            db.session.commit()
            return make_response(
                jsonify({"msg": f"created category {category.name}"}), 201
            )
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        category = Category.query.filter_by(id=id).first()
        if not category:
            return make_response(jsonify({"msg": "Category not found"}), 404)

        data = request.get_json()
        try:
            category.name = data.get("name", category.name)
            category.slug = data.get("slug", category.slug)
            category.description = data.get("description", category.description)
            category.parent_id = data.get("parent_id", category.parent_id)
            category.image_url = data.get("image_url", category.image_url)
            db.session.commit()
            return make_response(jsonify(category.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        category = Category.query.filter_by(id=id).first()
        if not category:
            return make_response(jsonify({"msg": "Category not found"}), 404)

        try:
            db.session.delete(category)
            db.session.commit()
            return make_response(jsonify({"msg": "Category deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class BrandResource(Resource):
    # @authorised_route("super_admin")
    def get(self, id=None):
        if id is None:
            brands = [b.to_dict() for b in Brand.query.all()]
            return make_response(jsonify(brands), 200)
        else:
            brand = Brand.query.filter_by(id=id).first()
            if not brand:
                return make_response(jsonify({"msg": "Brand not found"}), 404)
            return make_response(jsonify(brand.to_dict()), 200)

    def post(self):
        data = request.get_json()
        existing_brand = Brand.query.filter_by(name=data["name"]).first()
        if existing_brand:
            return make_response(
                jsonify({"msg": f"existing brand {existing_brand.name}"}), 409
            )
        try:
            brand = Brand(
                name=data["name"],
                slug=data["slug"],
                description=data.get("description"),
                logo_url=data.get("logo_url"),
                website=data.get("website"),
                country_of_origin=data.get("country_of_origin"),
                year_established=data.get("year_established"),
            )
            db.session.add(brand)
            db.session.commit()
            return make_response(
                jsonify({"msg": f"create {brand.name} sucessfully"}), 201
            )
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        brand = Brand.query.filter_by(id=id).first()
        if not brand:
            return make_response(jsonify({"msg": "Brand not found"}), 404)

        data = request.get_json()
        try:
            brand.name = data.get("name", brand.name)
            brand.slug = data.get("slug", brand.slug)
            brand.description = data.get("description", brand.description)
            brand.logo_url = data.get("logo_url", brand.logo_url)
            brand.website = data.get("website", brand.website)
            brand.country_of_origin = data.get(
                "country_of_origin", brand.country_of_origin
            )
            brand.year_established = data.get(
                "year_established", brand.year_established
            )
            db.session.commit()
            return make_response(jsonify(brand.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        brand = Brand.query.filter_by(id=id).first()
        if not brand:
            return make_response(jsonify({"msg": "Brand not found"}), 404)

        try:
            db.session.delete(brand)
            db.session.commit()
            return make_response(jsonify({"msg": "Brand deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class RoleResource(Resource):
    def get(self, id=None):
        if id is None:
            roles = [r.to_dict() for r in Role.query.all()]
            return make_response(jsonify(roles), 200)
        else:
            role = Role.query.filter_by(id=id).first()
            if not role:
                return make_response(jsonify({"msg": "Role not found"}), 404)
            return make_response(jsonify(role.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            existing_role = Role.query.filter_by(name=data["name"]).first()
            if existing_role:
                return make_response(jsonify({"msg": "Role already exists"}))

            role = Role(name=data["name"], level=data["level"])
            db.session.add(role)
            db.session.commit()

            return make_response(
                jsonify({"msg": f"Role {role.name} created sucessfully"})
            )
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig)
            return make_response(jsonify({"msg": f" {error_message}"}), 400)

        except ValueError as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

        except Exception as e:
            db.session.rollback()
            return make_response(
                jsonify({"msg": "Something went wrong", "error": str(e)}), 500
            )

    def patch(self, id):
        data = request.get_json()
        role = Role.query.filter_by(id=id).first()
        if not role:
            return make_response(jsonify({"msg": "Role could not be found"}), 404)
        try:
            role.name = data.get("name", role.name)
            role.level = data.get("level", role.level)
            db.session.commit()
            return make_response(
                jsonify({"msg": f"Role {role.name} updated sucessfully"})
            )

        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig)
            return make_response(jsonify({"msg": f" {error_message}"}), 400)

        except ValueError as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

        except Exception as e:
            db.session.rollback()
            return make_response(
                jsonify({"msg": "Something went wrong", "error": str(e)}), 500
            )

    def delete(self, id):
        role = Role.query.filter_by(id=id).first()
        if not role:
            return make_response(jsonify({"msg": "Role could not be found"}), 404)
        try:
            db.session.delete(role)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class ProductResource(Resource):
    def get(self, id=None):
        if id is None:
            # Get pagination parameters from query string
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)

            # Paginate products
            paginated_products = Product.query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            # Serialize paginated results
            products = [p.to_dict() for p in paginated_products.items]

            return make_response(
                jsonify(
                    {
                        "content": products,
                        "total": paginated_products.total,  # Total number of products
                        "pages": paginated_products.pages,  # Total pages available
                        "current_page": paginated_products.page,
                        "per_page": paginated_products.per_page,
                        "has_next": paginated_products.has_next,  # Boolean: Is there a next page?
                        "has_prev": paginated_products.has_prev,  # Boolean: Is there a previous page?
                    }
                ),
                200,
            )
        else:
            product = Product.query.filter_by(id=id).first()
            if not product:
                return make_response(jsonify({"msg": "Product not found"}), 404)
            product_data = product.to_dict()
            product_data["images"] = [image.url for image in product.images]

            return make_response(jsonify(product_data), 200)

    def post(self):
        data = request.get_json()
        try:
            product = Product(
                name=data["name"],
                sku=data["sku"],
                description=data["description"],
                price=data["price"],
                cost=data.get("cost"),
                discount=data.get("discount"),
                category_id=data["category_id"],
                brand_id=data.get("brand_id"),
                stock=data.get("stock", 0),
                weight=data.get("weight"),
                dimensions=data.get("dimensions"),
                features=data.get("features"),
                specifications=data.get("specifications"),
                status=data.get("status", "Active"),
                meta_title=data.get("meta_title"),
                meta_description=data.get("meta_description"),
                is_featured=data.get("is_featured", False),
                compatible_makes=data.get("compatible_makes"),
                compatible_models=data.get("compatible_models"),
            )
            db.session.add(product)
            db.session.commit()
            return make_response(jsonify(product.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        product = Product.query.filter_by(id=id).first()
        if not product:
            return make_response(jsonify({"msg": "Product not found"}), 404)

        data = request.get_json()
        try:
            for field in [
                "name",
                "sku",
                "description",
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
            ]:
                if field in data:
                    setattr(product, field, data[field])

            db.session.commit()
            return make_response(jsonify(product.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        product = Product.query.filter_by(id=id).first()
        if not product:
            return make_response(jsonify({"msg": "Product not found"}), 404)

        try:
            db.session.delete(product)
            db.session.commit()
            return make_response(jsonify({"msg": "Product deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class ProductRoute(Resource):
    def post(self):
        if not request.content_type.startswith("multipart/form-data"):
            return {"msg": "Unsupported Media Type: Use multipart/form-data"}, 415

        data = request.form
        images = request.files.getlist("images")

        # Validate required fields and images
        required_fields = ["name", "sku", "description", "price", "category_id"]
        for field in required_fields:
            if field not in data:
                return {"msg": f"Missing required field: {field}"}, 400
        if not images:
            return {"msg": "At least one image is required"}, 400
        if not images or all(image.filename == "" for image in images):
            return {"msg": "At least one valid image is required."}, 400
        saved_images = []
        try:
            # Process images
            upload_dir = app.config["UPLOAD_DIR"]
            allowed_extensions = app.config["ALLOWED_EXTENSIONS"]

            # Process images
            for idx, image in enumerate(images):
                if image.filename == "":
                    continue

                # Validate file extension
                filename = secure_filename(image.filename)
                if (
                    "." not in filename
                    or filename.split(".")[-1].lower() not in allowed_extensions
                ):
                    return {"msg": "File type not allowed"}, 400

                # Generate unique filename
                unique_filename = f"{uuid.uuid4().hex[:6]}_{filename}"
                save_path = os.path.join(
                    upload_dir, unique_filename
                )  # Use config-defined path

                # Save file
                image.save(save_path)

                # Construct URL using configurable domain (if needed)
                # base_url = request.host_url.rstrip("/") # to revisit
                server_public_ip_url = "http://54.210.214.53"  # temporary
                full_url = urljoin(
                    server_public_ip_url, f"{upload_dir}/{unique_filename}"
                )
                saved_images.append({"url": full_url, "is_primary": idx == 0})
            # check for branch
            existing_branch = Category.query.filter_by(
                id=int(data["branch_id"])
            ).first()
            if not existing_branch:
                return make_response(jsonify({"msg": "Branch not found"}), 404)

            existing_category = Category.query.filter_by(
                id=int(data["category_id"])
            ).first()
            if not existing_category:
                return make_response(jsonify({"msg": "Category not found"}), 404)
            product = Product(
                name=data["name"],
                sku=data["sku"],
                description=data["description"],
                imgUrl=saved_images[0]["url"],  # Full URL here
                price=float(data["price"]),
                category_id=existing_category.id,
                cost=data.get("cost"),
                discount=data.get("discount"),
                brand_id=existing_branch.id,
                stock=data.get("stock", 0),
                weight=data.get("weight"),
                dimensions=data.get("dimensions"),
                features=data.get("features"),
                specifications=data.get("specifications"),
                status=data.get("status", "Active"),
                meta_title=data.get("meta_title"),
                meta_description=data.get("meta_description"),
                is_featured=str_to_bool(data.get("is_featured", False)),
                compatible_makes=data.get("compatible_makes"),
                compatible_models=data.get("compatible_models"),
            )
            db.session.add(product)
            db.session.flush()  # Get product ID for images

            # Create ProductImage entries
            for img_data in saved_images:
                img = ProductImage(
                    product_id=product.id,
                    url=img_data["url"],
                    is_primary=img_data["is_primary"],
                )
                db.session.add(img)

            db.session.commit()
            return make_response(
                jsonify({"msg": f"product {product.name} created suceesfully"}), 201
            )
        except IntegrityError as e:
            db.session.rollback()
            error_message = str(e.orig)
            return make_response(jsonify({"msg": f" {error_message}"}), 400)

        except Exception as e:
            db.session.rollback()
            for img in saved_images:
                try:
                    file_path = os.path.join(
                        "static", "assets", img["url"].split("/")[-1]
                    )
                    os.remove(file_path)
                except Exception:
                    pass
            error_msg = str(e).split("\n")[0]

            return make_response(jsonify({"msg": error_msg}), 400)


class CustomerResource(Resource):
    def get(self, id=None):
        if id is None:
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)

            # Paginate content
            paginated_content = Customer.query.paginate(
                page=page, per_page=per_page, error_out=False
            )

            customers = [c.to_dict() for c in paginated_content.items]
            return make_response(
                jsonify(
                    {
                        "content": customers,
                        "total": paginated_content.total,  # Total number of products
                        "pages": paginated_content.pages,  # Total pages available
                        "current_page": paginated_content.page,
                        "per_page": paginated_content.per_page,
                        "has_next": paginated_content.has_next,  # Boolean: Is there a next page?
                        "has_prev": paginated_content.has_prev,  # Boolean: Is there a previous page?
                    }
                ),
                200,
            )
        else:
            customer = Customer.query.filter_by(id=id).first()
            if not customer:
                return make_response(jsonify({"msg": "Customer not found"}), 404)
            return make_response(jsonify(customer.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            customer = Customer(
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                phone=data.get("phone"),
                user_id=data.get("user_id"),
            )
            db.session.add(customer)
            db.session.commit()
            return make_response(jsonify(customer.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        customer = Customer.query.filter_by(id=id).first()
        if not customer:
            return make_response(jsonify({"msg": "Customer not found"}), 404)

        data = request.get_json()
        try:
            customer.first_name = data.get("first_name", customer.first_name)
            customer.last_name = data.get("last_name", customer.last_name)
            customer.email = data.get("email", customer.email)
            customer.phone = data.get("phone", customer.phone)
            customer.user_id = data.get("user_id", customer.user_id)
            db.session.commit()
            return make_response(jsonify(customer.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        customer = Customer.query.filter_by(id=id).first()
        if not customer:
            return make_response(jsonify({"msg": "Customer not found"}), 404)

        try:
            db.session.delete(customer)
            db.session.commit()
            return make_response(jsonify({"msg": "Customer deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class AddressResource(Resource):
    def get(self, id=None):
        if id is None:
            addresses = [a.to_dict() for a in Address.query.all()]
            return make_response(jsonify(addresses), 200)
        else:
            address = Address.query.filter_by(id=id).first()
            if not address:
                return make_response(jsonify({"msg": "Address not found"}), 404)
            return make_response(jsonify(address.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            address = Address(
                customer_id=data["customer_id"],
                address_line=data["address_line"],
                county=data["county"],
                town=data["town"],
                postal_code=data.get("postal_code"),
                is_default=data.get("is_default", False),
            )
            db.session.add(address)
            db.session.commit()
            return make_response(jsonify(address.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        address = Address.query.filter_by(id=id).first()
        if not address:
            return make_response(jsonify({"msg": "Address not found"}), 404)

        data = request.get_json()
        try:
            address.customer_id = data.get("customer_id", address.customer_id)
            address.address_line = data.get("address_line", address.address_line)
            address.county = data.get("county", address.county)
            address.town = data.get("town", address.town)
            address.postal_code = data.get("postal_code", address.postal_code)
            address.is_default = data.get("is_default", address.is_default)
            db.session.commit()
            return make_response(jsonify(address.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        address = Address.query.filter_by(id=id).first()
        if not address:
            return make_response(jsonify({"msg": "Address not found"}), 404)

        try:
            db.session.delete(address)
            db.session.commit()
            return make_response(jsonify({"msg": "Address deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class OrderResource(Resource):
    def get(self, id=None):
        if id is None:
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)

            # Paginate content
            paginated_content = Order.query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            orders = [o.to_dict() for o in paginated_content.items]
            return make_response(
                jsonify(
                    {
                        "content": orders,
                        "total": paginated_content.total,  # Total number of products
                        "pages": paginated_content.pages,  # Total pages available
                        "current_page": paginated_content.page,
                        "per_page": paginated_content.per_page,
                        "has_next": paginated_content.has_next,  # Boolean: Is there a next page?
                        "has_prev": paginated_content.has_prev,  # Boolean: Is there a previous page?
                    }
                ),
                200,
            )
        else:
            order = Order.query.filter_by(id=id).first()
            if not order:
                return make_response(jsonify({"msg": "Order not found"}), 404)
            return make_response(jsonify(order.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            order = Order(
                customer_id=data["customer_id"],
                order_number=data["order_number"],
                status=data["status"],
                total_amount=data["total_amount"],
                shipping_address_id=data["shipping_address_id"],
                billing_address_id=data.get("billing_address_id"),
                payment_method=data["payment_method"],
                payment_status=data["payment_status"],
                shipping_method=data.get("shipping_method"),
                shipping_cost=data.get("shipping_cost"),
                tax_amount=data.get("tax_amount"),
                discount_amount=data.get("discount_amount"),
                notes=data.get("notes"),
                delivery_company=data.get("delivery_company"),
                tracking_number=data.get("tracking_number"),
                delivery_person=data.get("delivery_person"),
                estimated_delivery_date=data.get("estimated_delivery_date"),
            )
            db.session.add(order)
            db.session.commit()
            return make_response(jsonify(order.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        order = Order.query.filter_by(id=id).first()
        if not order:
            return make_response(jsonify({"msg": "Order not found"}), 404)

        data = request.get_json()
        try:
            for field in [
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
            ]:
                if field in data:
                    setattr(order, field, data[field])

            db.session.commit()
            return make_response(jsonify(order.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        order = Order.query.filter_by(id=id).first()
        if not order:
            return make_response(jsonify({"msg": "Order not found"}), 404)

        try:
            db.session.delete(order)
            db.session.commit()
            return make_response(jsonify({"msg": "Order deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class OrderItemResource(Resource):
    def get(self, id=None):
        if id is None:
            items = [i.to_dict() for i in OrderItem.query.all()]
            return make_response(jsonify(items), 200)
        else:
            item = OrderItem.query.filter_by(id=id).first()
            if not item:
                return make_response(jsonify({"msg": "Order item not found"}), 404)
            return make_response(jsonify(item.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            item = OrderItem(
                order_id=data["order_id"],
                product_id=data["product_id"],
                quantity=data["quantity"],
                unit_price=data["unit_price"],
                total_price=data["total_price"],
            )
            db.session.add(item)
            db.session.commit()
            return make_response(jsonify(item.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        item = OrderItem.query.filter_by(id=id).first()
        if not item:
            return make_response(jsonify({"msg": "Order item not found"}), 404)

        data = request.get_json()
        try:
            item.order_id = data.get("order_id", item.order_id)
            item.product_id = data.get("product_id", item.product_id)
            item.quantity = data.get("quantity", item.quantity)
            item.unit_price = data.get("unit_price", item.unit_price)
            item.total_price = data.get("total_price", item.total_price)
            db.session.commit()
            return make_response(jsonify(item.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        item = OrderItem.query.filter_by(id=id).first()
        if not item:
            return make_response(jsonify({"msg": "Order item not found"}), 404)

        try:
            db.session.delete(item)
            db.session.commit()
            return make_response(jsonify({"msg": "Order item deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class UserResource(Resource):
    def get(self, id=None):
        if id is None:
            users = [u.to_dict() for u in User.query.all()]
            return make_response(jsonify(users), 200)
        else:
            user = User.query.filter_by(id=id).first()
            if not user:
                return make_response(jsonify({"msg": "User not found"}), 404)
            return make_response(jsonify(user.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            user = User(
                email=data["email"],
                password_hash=data[
                    "password_hash"
                ],  # Note: You should hash the password before storing
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                is_active=data.get("is_active", True),
            )
            db.session.add(user)
            db.session.commit()
            return make_response(jsonify(user.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        user = User.query.filter_by(id=id).first()
        if not user:
            return make_response(jsonify({"msg": "User not found"}), 404)

        data = request.get_json()
        try:
            user.email = data.get("email", user.email)
            if "password_hash" in data:
                user.password_hash = data["password_hash"]  # Remember to hash this
            user.first_name = data.get("first_name", user.first_name)
            user.last_name = data.get("last_name", user.last_name)
            user.is_active = data.get("is_active", user.is_active)
            db.session.commit()
            return make_response(jsonify(user.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        user = User.query.filter_by(id=id).first()
        if not user:
            return make_response(jsonify({"msg": "User not found"}), 404)

        try:
            db.session.delete(user)
            db.session.commit()
            return make_response(jsonify({"msg": "User deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class ReviewResource(Resource):
    def get(self, id=None):
        if id is None:
            reviews = [r.to_dict() for r in Review.query.all()]
            return make_response(jsonify(reviews), 200)
        else:
            review = Review.query.filter_by(id=id).first()
            if not review:
                return make_response(jsonify({"msg": "Review not found"}), 404)
            return make_response(jsonify(review.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            review = Review(
                product_id=data["product_id"],
                customer_id=data.get("customer_id"),
                rating=data["rating"],
                comment=data.get("comment"),
                is_approved=data.get("is_approved", False),
            )
            db.session.add(review)
            db.session.commit()
            return make_response(jsonify(review.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        review = Review.query.filter_by(id=id).first()
        if not review:
            return make_response(jsonify({"msg": "Review not found"}), 404)

        data = request.get_json()
        try:
            review.product_id = data.get("product_id", review.product_id)
            review.customer_id = data.get("customer_id", review.customer_id)
            review.rating = data.get("rating", review.rating)
            review.comment = data.get("comment", review.comment)
            review.is_approved = data.get("is_approved", review.is_approved)
            db.session.commit()
            return make_response(jsonify(review.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        review = Review.query.filter_by(id=id).first()
        if not review:
            return make_response(jsonify({"msg": "Review not found"}), 404)

        try:
            db.session.delete(review)
            db.session.commit()
            return make_response(jsonify({"msg": "Review deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


class InventoryLogResource(Resource):
    def get(self, id=None):
        if id is None:
            logs = [log.to_dict() for log in InventoryLog.query.all()]
            return make_response(jsonify(logs), 200)
        else:
            log = InventoryLog.query.filter_by(id=id).first()
            if not log:
                return make_response(jsonify({"msg": "Inventory log not found"}), 404)
            return make_response(jsonify(log.to_dict()), 200)

    def post(self):
        data = request.get_json()
        try:
            log = InventoryLog(
                product_id=data["product_id"],
                quantity_change=data["quantity_change"],
                previous_stock=data["previous_stock"],
                new_stock=data["new_stock"],
                change_type=data["change_type"],
                reference_id=data.get("reference_id"),
                notes=data.get("notes"),
                created_by=data.get("created_by"),
            )
            db.session.add(log)
            db.session.commit()
            return make_response(jsonify(log.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def patch(self, id):
        log = InventoryLog.query.filter_by(id=id).first()
        if not log:
            return make_response(jsonify({"msg": "Inventory log not found"}), 404)

        data = request.get_json()
        try:
            log.product_id = data.get("product_id", log.product_id)
            log.quantity_change = data.get("quantity_change", log.quantity_change)
            log.previous_stock = data.get("previous_stock", log.previous_stock)
            log.new_stock = data.get("new_stock", log.new_stock)
            log.change_type = data.get("change_type", log.change_type)
            log.reference_id = data.get("reference_id", log.reference_id)
            log.notes = data.get("notes", log.notes)
            log.created_by = data.get("created_by", log.created_by)
            db.session.commit()
            return make_response(jsonify(log.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

    def delete(self, id):
        log = InventoryLog.query.filter_by(id=id).first()
        if not log:
            return make_response(jsonify({"msg": "Inventory log not found"}), 404)

        try:
            db.session.delete(log)
            db.session.commit()
            return make_response(jsonify({"msg": "Inventory log deleted"}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)


def process_order():
    """Main function to handle the entire transaction."""
    data = request.get_json()

    try:
        # Start transaction
        customer, is_new_customer = get_or_create_customer(data)
        db.session.flush()

        address, is_new_shipping = get_or_create_address(data, customer.id)
        db.session.flush()

        order = create_order(data, customer.id, address.id)
        db.session.flush()  # Flush to get order ID

        create_order_items(data["order_items"], order.id)

        # Commit transaction
        db.session.commit()

        return make_response(
            jsonify({"msg": "Order placed successfully", "order": order.to_dict()}), 201
        )

    except IntegrityError as e:
        db.session.rollback()
        return make_response(
            jsonify({"msg": "Database Integrity Error", "error": str(e)}), 400
        )

    except ValueError as e:
        db.session.rollback()
        return make_response(jsonify({"msg": str(e)}), 400)

    except Exception as e:
        db.session.rollback()
        return make_response(
            jsonify({"msg": "Something went wrong", "error": str(e)}), 500
        )


class OrderProcess(Resource):
    def post(self):
        data = request.get_json()
        try:
            customer, is_new_customer = get_or_create_customer(data["customer"])
            db.session.flush()

            shipping_address, is_new_shipping = get_or_create_address(
                data["address"], customer.id
            )
            db.session.flush()

            order = create_order(data["order"], customer.id, shipping_address.id)
            db.session.flush()

            create_order_items(data["order_items"], order.id)

            # Commit transaction
            db.session.commit()

            return make_response(
                jsonify({"msg": "Order placed successfully", "order": order.to_dict()}),
                201,
            )

        except IntegrityError as e:
            db.session.rollback()
            return make_response(
                jsonify({"msg": "Database Integrity Error", "error": str(e)}), 400
            )

        except ValueError as e:
            db.session.rollback()
            return make_response(jsonify({"msg": str(e)}), 400)

        except Exception as e:
            db.session.rollback()
            return make_response(
                jsonify({"msg": "Something went wrong", "error": str(e)}), 500
            )
