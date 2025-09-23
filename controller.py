from flask import Blueprint, app, render_template, request, redirect, url_for, flash, session
from models import db, Customer, Order, OrderItem, DeliveryPerson, DiscountCode, DiscountType, Admin, Pizza, pizza_ingredient, Ingredient
from werkzeug.security import check_password_hash
import os
from datetime import datetime


main_bp = Blueprint('main', __name__)
menu_bp = Blueprint('menu', __name__)
order_bp = Blueprint('order', __name__)
customer_bp = Blueprint('customer', __name__)
admin_bp = Blueprint('admin', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

PEPPER = os.environ.get('PASSWORD_PEPPER', 'default-pepper-change-in-production')

def verify_password_with_pepper(password, password_hash):
    """Verify password with pepper"""
    peppered_password = password + PEPPER
    return check_password_hash(password_hash, peppered_password)

#-------------------------------


@customer_bp.route('/customer/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
        address = request.form.get('address')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([first_name, last_name, email, telephone, address, password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template("customer_register.html")
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template("customer_register.html")
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template("customer_register.html")
        
        # Check if email already exists
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer:
            flash('Email address already registered. Please use a different email.', 'error')
            return render_template("customer_register.html")
        
        try:
            # Create new customer
            from werkzeug.security import generate_password_hash
            peppered_password = password + PEPPER
            password_hash = generate_password_hash(peppered_password)
            
            new_customer = Customer(
                first_name=first_name,
                last_name=last_name,
                email=email,
                telephone=telephone,
                address=address,
                password_hash=password_hash
            )
            
            db.session.add(new_customer)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('customer.login'))  # You'll need to create this login route too
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template("customer_register.html")
    
    return render_template("customer_register.html")

# Add this after your customer registration route:

@customer_bp.route('/customer/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validation
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template("customer_login.html")
        
        # Query the customer from the database
        customer = Customer.query.filter_by(email=email).first()
        
        if customer and verify_password_with_pepper(password, customer.password_hash):
            # Set session variables
            session['customer_id'] = customer.customer_id
            session['customer_email'] = customer.email
            session['customer_name'] = f"{customer.first_name} {customer.last_name}"
            flash('Login successful! Welcome back!', 'success')
            return redirect(url_for('main.index'))  # Redirect to homepage or customer dashboard
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template("customer_login.html")

@customer_bp.route('/customer/logout')
def logout():
    # Clear customer session
    session.pop('customer_id', None)
    session.pop('customer_email', None)
    session.pop('customer_name', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main.index'))

@main_bp.route("/menu")
def menu():
    pizzas = Pizza.query.all()
    return {"pizzas": [pizza.name for pizza in pizzas]}





######## BELOW IS THE CONTROLLER FOR THE ADMIN DASHBOARD, THIS CAN ONLY BE ACCESSED USING AN ADMIN ACCOUNT

#---------------------ADMIN DASHBOARD ---------------------------------

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query the admin from the database
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and verify_password_with_pepper(password, admin.password_hash):
            # Set session variables
            session['admin_id'] = admin.admin_id
            session['admin_username'] = admin.username
            flash('Login successful!', 'success')
            return redirect(url_for('admin.dashboard'))  # Ensure this route exists
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template("admin_login.html")

@admin_bp.route('/admin/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    # Get counts for dashboard overview
    stats = {
        'customers': Customer.query.count(),
        'pizzas': Pizza.query.count(),
        'ingredients': Ingredient.query.count(),
        'orders': Order.query.count(),
        'delivery_people': DeliveryPerson.query.count(),
        'discount_codes': DiscountCode.query.count(),
        'discount_types': DiscountType.query.count()
    }
    
    # Get recent data for dashboard
    recent_customers = Customer.query.order_by(Customer.customer_id.desc()).limit(5).all()
    recent_orders = Order.query.order_by(Order.order_id.desc()).limit(5).all()
    
    return render_template("admin_dashboard.html", stats=stats, recent_customers=recent_customers, recent_orders=recent_orders)

################ DONE ############
@admin_bp.route('/admin/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('admin.admin_login'))
####################################

# ---------------------- CUSTOMER ADMIN -------------------------
# Update your existing customers route:
@admin_bp.route('/admin/customers')
def customers():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    customers = Customer.query.order_by(Customer.customer_id.asc()).all()
    
    # Calculate basic stats
    stats = {
        'total_customers': len(customers),
        'customers_with_orders': len([c for c in customers if hasattr(c, 'orders') and c.orders]),
    }
    
    return render_template("admin_customers.html", customers=customers, stats=stats)
# --------------------PIZZA ADMIN-----------------------------------
# Pizza Management
@admin_bp.route('/admin/pizzas')
def pizzas():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    # Order pizzas by ID (ascending)
    pizzas = Pizza.query.order_by(Pizza.pizza_id.asc()).all()
    return render_template("admin_pizzas.html", pizzas=pizzas)

# ---------------------------------------------------------------------#

#--------------------INGREDIENTS ADMIN ----------------------------------
# Your existing ingredients route is already correct:
@admin_bp.route('/admin/ingredients')
def ingredients():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    # Order ingredients by ID for consistency
    ingredients = Ingredient.query.order_by(Ingredient.ingredient_id.asc()).all()
    return render_template("admin_ingredients.html", ingredients=ingredients)


# ---------------------DELIVERY PERSON ADMIN -------------------------------
@admin_bp.route('/admin/delivery-people')
def delivery_people():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    delivery_people = DeliveryPerson.query.all()
    return render_template("admin_delivery_people.html", delivery_people=delivery_people)

#------------------------DISCOUNT ADMIN -----------------------------------
@admin_bp.route('/admin/discount-types')
def discount_types():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    discount_types = DiscountType.query.all()
    return render_template("admin_discount_types.html", discount_types=discount_types)

@admin_bp.route('/admin/discount-codes')
def discount_codes():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    discount_codes = DiscountCode.query.all()
    return render_template("admin_discount_codes.html", discount_codes=discount_codes)

#------------------------ORDERS ADMIN --------------------------------------
@admin_bp.route('/admin/orders')
def orders():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    orders = Order.query.order_by(Order.order_id.desc()).all()
    return render_template("admin_orders.html", orders=orders)

# add these simple routes so the index page can redirect to them without errors
@main_bp.route("/customer/login", methods=["GET"])
def customer_login():
    return render_template("customer_login.html")

@main_bp.route("/customer/register", methods=["GET"])
def customer_register():
    return render_template("customer_register.html")
