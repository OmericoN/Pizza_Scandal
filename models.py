from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = "Customers"
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<CustomerID {self.customer_id} First Name {self.first_name} address {self.address}"
    

class DiscountCode(db.Model):
    __tablename__="DiscountCode"
    discount_code_id = db.Column(db.Integer, primary_key=True, )


