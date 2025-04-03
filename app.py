# app.py
from config import app, db
import os
from blueprint import api_v1_blueprint

app.register_blueprint(api_v1_blueprint)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    upload_dir = app.config["UPLOAD_DIR"]
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    app.run(port=5000, debug=True)
    # scheduler.start()
