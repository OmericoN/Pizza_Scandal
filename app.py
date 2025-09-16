from flask import Flask, request
from dotenv import load_dotenv
import os
from models import db

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-key-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI") #Uses a .env to hide password (I'll help you set it up Raul)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return ("<p>Pizzeria app. Supabase connection is working</p>")
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
