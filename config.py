# config.py
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from datetime import timedelta

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(weeks=5215)
app.config["JWT_SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["MAIL_SERVER"] = "smtp.googlemail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["UPLOAD_DIR"] = os.path.join(
    "static", "assets"
)  # Directory for storing images
app.config["ALLOWED_EXTENSIONS"] = {
    "png",
    "jpg",
    "jpeg",
    "webp",
}  # Permitted image formats
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.json.compact = False
metadata = MetaData(
    naming_convention={
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
)

# Initialize database and migration
db = SQLAlchemy(metadata=metadata)
db.init_app(app)
blacklist = set()
jwt = JWTManager()
jwt.init_app(app)

api = Api(app)
mail = Mail(app)
migrate = Migrate(app, db)
CORS(app)
