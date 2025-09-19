from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()


deliveryPerson_Order = db.Table(
    'deliveryperson_order',
    db.Column('delivery_person_id', db.Integer, db.ForeignKey('DeliveryPerson.delivery_person_id'), primary_key = True),
    db.Column('order_id', db.Integer, db.ForeignKey('Order.order_id'), primary_key = True)
)


pizza_ingredients = db.Table(
   'pizza_ingredients',
   db.Column('pizza_id', db.Integer, db.ForeignKey('Pizza.pizza_id'), primary_key=True),
   db.Column('ingredient_id', db.Integer, db.ForeignKey('Ingredients.ingredient_id'), primary_key=True)
)

discount_list = db.Table(
    'discount_list',
    db.Column('discount_code_id', db.Integer, db.ForeignKey('DiscountCode.discount_code_id'), primary_key=True),
    db.Column('discount_type_id', db.Integer, db.ForeignKey('DiscountType.discount_type_id'), primary_key=True)
)

class Customer(db.Model):
    __tablename__ = "Customer"
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
    discount_type = db.relationship(
        'DiscountType',
        secondary=discount_list,
        back_populates='discount_code'
    )
    def __repr__(self):
        return f"discount code id {self.discount_code_id}, code: {self.code}"

class DiscountType(db.Model):
    __tablename__="DiscountType"
    discount_type_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    percent = db.Column(db.Numeric(5,2))


class Pizza(db.Model):
   __tablename__ = "Pizza"
   pizza_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   name = db.Column(db.String(100), nullable=False)
   price = db.Column(db.Numeric(5,2), nullable=False)
   description = db.Column(db.String(200), nullable=False)
   ingredients = db.relationship(
       'Ingredient',
       secondary=pizza_ingredients,
       back_populates='pizzas'
   )
   def compute_and_set_price(self):
       base_cost = sum(float(Ingredient.cost) for ingredient in self.ingredients)
       margin = 0.4
       vat = 0.09 #temp VAT for now
       self.price = round(base_cost * (1+margin) * (1+vat), 2)

   def __repr__(self):
       return f"Pizza id: {self.pizza_id}, name: {self.name}"


class Ingredient(db.Model):
   __tablename__ = "Ingredients"
   ingredient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   name = db.Column(db.String(100), nullable=False)
   cost = db.Column(db.Numeric(10, 2), nullable=False)
   vegetarian = db.Column(db.Boolean, nullable=False, default=False)
   pizzas = db.relationship(
       'Pizza',
       secondary=pizza_ingredients,
       back_populates='ingredients'
   )
   def __repr__(self):
       return f"id: {self.ingredient_id}, name: {self.name}, cost: {self.cost}"

class OrderItem(db.Model):
    __tablename__ = "OrderItem"
    order_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("Order.order_id"), nullable=False)
    pizza_id = db.Column(db.Integer, db.ForeignKey("Pizza.pizza_id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(7,2), nullable=False)

#order is connected to every other table too, how to deal with that? 
class Order(db.Model):
    __tablename__ = "Order"
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    discount_code_id = db.Column(db.Integer, db.ForeignKey("DiscountCode.discount_code_id"), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey("DeliveryPerson.delivery_person_id"))
    customer_id = db.Column(db.Integer, db.ForeignKey("Customer.customer_id"), nullable=False)
    total_price = db.Column(db.Numeric(7,2), nullable=False)

    order_items = db.relationship("OrderItem", backref="order", lazy=True)
    deliverypersons = db.relationship(
        'DeliveryPerson',
        secondary=deliveryPerson_Order,
        back_populates='orders'
    )

class DeliveryPerson(db.Model):
    __tablename__ = "DeliveryPerson"
    delivery_person_id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable=False)
    
    orders = db.relationship(
        'Order',
        secondary=deliveryPerson_Order,
        back_populates='deliverypersons'
    )



   ###

