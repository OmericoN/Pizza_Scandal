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
    discount_code_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    is_redeemed = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"discount code id {self.discount_code_id}, code: {self.code}"

class DiscountType(db.Model):
    __tablename__="DiscountType"
    discount_type_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    percent = db.Column(db.Numeric(5,2))

pizza_ingredients = db.Table(
   'pizza_ingredients',
   db.Column('pizza_id', db.Integer, db.ForeignKey('Pizza.pizza_id'), primary_key=True),
   db.Column('ingredient_id', db.Integer, db.ForeignKey('Ingredients.ingredient_id'), primary_key=True)
)


class Pizza(db.Model):
   __tablename__ = "Pizza"
   pizza_id = db.Column(db.Integer, primary_key=True)
   name = db.Column(db.String(100), nullable=False)
   description = db.Column(db.String(200), nullable=False)
   ingredients = db.relationship(
       'Ingredient',
       secondary=pizza_ingredients,
       back_populates='pizzas'
   )


class Ingredient(db.Model):
   __tablename__ = "Ingredients"
   ingredient_id = db.Column(db.Integer, primary_key=True)
   name = db.Column(db.String(100), nullable=False)
   cost = db.Column(db.Numeric(10, 2), nullable=False)
   vegetarian = db.Column(db.Boolean, nullable=False, default=False)
   pizzas = db.relationship(
       'Pizza',
       secondary=pizza_ingredients,
       back_populates='ingredients'
   )

   ###

