from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone, date
from sqlalchemy import SmallInteger, Column
import os

load_dotenv()
db = SQLAlchemy()



pizza_ingredient = db.Table(
   'pizza_ingredient',
   db.Column('pizza_id', db.Integer, db.ForeignKey('Pizza.pizza_id'), primary_key=True),
   db.Column('ingredient_id', db.Integer, db.ForeignKey('Ingredient.ingredient_id'), primary_key=True)
)

class Customer(db.Model):
    __tablename__ = "Customer"
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    telephone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    postal_code = db.Column(db.String(10))
    gender = db.Column(db.String(10), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    loyalty_pizza_count = db.Column(db.Integer, default=0)
    def set_password(self, password):
        # Add pepper to password before hashing
        pepper = os.environ.get('PASSWORD_PEPPER', 'default-pepper-change-in-production')
        peppered_password = password + pepper
        self.password_hash = generate_password_hash(peppered_password)

    def check_password(self, password):
        # Add pepper to password before checking
        pepper = os.environ.get('PASSWORD_PEPPER', 'default-pepper-change-in-production')
        peppered_password = password + pepper
        return check_password_hash(self.password_hash, peppered_password)
    
    def is_birthday_today(self):
        if not self.dob:
            return False
        
        today = date.today()
        # Fix: Change self.dob == today.month to self.dob.month == today.month
        return (self.dob.month == today.month and 
                self.dob.day == today.day)
    
    def add_pizzas_to_count(self, pizza_count):
        self.loyalty_pizza_count += pizza_count

    def __repr__(self):
        return f"<CustomerID {self.customer_id} First Name {self.first_name} address {self.address}>"

class DiscountCode(db.Model):
    __tablename__="DiscountCode"
    discount_code_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    # Foreign key to DiscountType
    discount_type_id = db.Column(db.Integer, db.ForeignKey("DiscountType.discount_type_id"), nullable=False)

    # Relationship to DiscountType
    discount_type = db.relationship("DiscountType", back_populates="discount_codes")

    def __repr__(self):
        return f"DiscountCode id: {self.discount_code_id}, code: {self.code}"

class DiscountType(db.Model):
    __tablename__="DiscountType"
    discount_type_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    percent = db.Column(db.Numeric(5,2))

    discount_codes = db.relationship("DiscountCode", back_populates="discount_type", lazy=True)


class Pizza(db.Model):
   __tablename__ = "Pizza"
   pizza_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   name = db.Column(db.String(100), nullable=False)
   description = db.Column(db.String(200), nullable=False)
   ingredients = db.relationship(
       'Ingredient',
       secondary=pizza_ingredient,
       back_populates='pizzas'
   )
   
   def __repr__(self):
       return f"Pizza id: {self.pizza_id}, name: {self.name}"


class Ingredient(db.Model):
   __tablename__ = "Ingredient"
   ingredient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
   name = db.Column(db.String(100), nullable=False)
   cost = db.Column(db.Numeric(10, 2), nullable=False)
   vegetarian = db.Column(db.Boolean, nullable=False, default=False)
   pizzas = db.relationship(
       'Pizza',
       secondary=pizza_ingredient,
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
    discount_code_id = db.Column(db.Integer, db.ForeignKey("DiscountCode.discount_code_id"), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("Customer.customer_id"), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey("DeliveryPerson.delivery_person_id"))  # Enforces one-to-one relationship
    total_price = db.Column(db.Numeric(7,2), nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  
    delivered_at = db.Column(db.DateTime, nullable=True)  

    order_items = db.relationship("OrderItem", backref="order", lazy=True)
    delivery_person = db.relationship("DeliveryPerson", backref=db.backref("orders", lazy=True))

    def get_status(self): 
        """Auto-calculate status based on elapsed time"""
        if self.status == 'delivered':
            return 'delivered'
        
        if not self.time_stamp:
            return 'pending'
        
        elapsed = datetime.now(timezone.utc) - self.time_stamp.replace(tzinfo=timezone.utc)
        minutes = elapsed.total_seconds() / 60
        
        if minutes < 10:
            return 'preparing'
        elif minutes < 30:
            return 'out_for_delivery'
        else:
            # Auto-mark as delivered after 30 minutes
            self.status = 'delivered'
            if not self.delivered_at:
                self.delivered_at = self.time_stamp + timedelta(minutes=30)
            db.session.commit()
            return 'delivered'
        
class DeliveryPerson(db.Model):
    __tablename__ = "DeliveryPerson"
    delivery_person_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(10))
    last_assigned_at = db.Column(db.DateTime, nullable=True)  # NEW

    postal_ranges = db.relationship(
        "DeliveryPersonPostalRange",
        back_populates="delivery_person",
        cascade="all, delete-orphan",
        lazy=True
    )

class DeliveryPersonPostalRange(db.Model):
    __tablename__ = "delivery_person_postal_range"
    delivery_person_id = db.Column(
        db.Integer,
        db.ForeignKey("DeliveryPerson.delivery_person_id"),
        primary_key=True
    )
    start_zip = db.Column(db.Integer, primary_key=True)
    end_zip = db.Column(db.Integer, primary_key=True)

    __table_args__ = (
        db.CheckConstraint('start_zip <= end_zip', name='ck_dppr_bounds'),
    )

    delivery_person = db.relationship("DeliveryPerson", back_populates="postal_ranges")

class Admin(db.Model):
    __tablename__ = "Admin"
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    def set_password(self, password):
        # Add pepper to password before hashing
        pepper = os.environ.get('PASSWORD_PEPPER', 'default-pepper-change-in-production')
        peppered_password = password + pepper
        self.password_hash = generate_password_hash(peppered_password)

    def check_password(self, password):
        # Add pepper to password before checking
        pepper = os.environ.get('PASSWORD_PEPPER', 'default-pepper-change-in-production')
        peppered_password = password + pepper
        return check_password_hash(self.password_hash, peppered_password)

    def __repr__(self):
        return f"<Admin {self.username}>"
   ###

def seed_data():
    today = date.today()
    if Customer.query.count() == 0:
        demo_customer = Customer(first_name="demo", last_name="demo", email="demo@pizzascandal.com", telephone="+000000000", address="le pizzeria, earth", postal_code="6200", gender="other", dob=date(1995, today.month, today.day))
        demo_customer.set_password("demo123")
        db.session.add(demo_customer)
    
    if Admin.query.count() == 0:
        admins = [
            {"username":"Omer", "password":"Omer1234"},
            {"username":"Raul", "password":"Raul1234"}
        ]
        for admin in admins:
            existing_admin = Admin.query.filter_by(username=admin["username"]).first()
            if not existing_admin:
                new_admin = Admin(username=admin["username"])
                new_admin.set_password(admin["password"])
                db.session.add(new_admin)

    if DiscountType.query.count() == 0:
        discount_types = [
            DiscountType(name="Birthday Discount", percent=15),
            DiscountType(name="One-Time Promo", percent=20),
            DiscountType(name="Loyalty Reward", percent=10)
        ]
        for dt in discount_types:
            db.session.add(dt)

    if DiscountCode.query.count() == 0:
        # Get the discount types we just created
        birthday_type = DiscountType.query.filter_by(name="Birthday Discount").first()
        onetime_type = DiscountType.query.filter_by(name="One-Time Promo").first()
        loyalty_type = DiscountType.query.filter_by(name="Loyalty Reward").first()
        
        discount_codes = [
            # Birthday discount code (automatic, no manual code needed, but we create one for system use)
            DiscountCode(
                code="BDAY15",
                discount_type_id=birthday_type.discount_type_id)
            ,DiscountCode(
                code="WELCOME20",
                discount_type_id=onetime_type.discount_type_id),
            DiscountCode(
                code="LOYAL10",
                discount_type_id=loyalty_type.discount_type_id)]
        for code in discount_codes:
            db.session.add(code)
            
    db.session.commit()
