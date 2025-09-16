from flask import Flask, request

def create_app():
    app = Flask(__name__)
    app.secret_key = "12345"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
