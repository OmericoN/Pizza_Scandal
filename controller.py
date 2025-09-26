from flask import Blueprint, app, render_template, request, redirect, url_for, flash, session
from models import db, Customer, Order, OrderItem, DeliveryPerson, DiscountCode, DiscountType, Admin, Pizza, pizza_ingredient, Ingredient
from werkzeug.security import check_password_hash
from sqlalchemy.orm import joinedload
from sqlalchemy import func
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
#hwllo



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
        
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer:
            flash('Email address already registered. Please use a different email.', 'error')
            return render_template("customer_register.html")
        
        try:
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
        
        customer = Customer.query.filter_by(email=email).first()
        
        if customer and verify_password_with_pepper(password, customer.password_hash):
            # Set session variables
            session['customer_id'] = customer.customer_id
            session['customer_email'] = customer.email
            session['customer_name'] = f"{customer.first_name} {customer.last_name}"
            flash('Login successful! Welcome back!', 'success')
            return redirect(url_for('customer.app'))  # Redirect to homepage or customer dashboard
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

@customer_bp.route('/customer/app')
def app():
    if 'customer_id' not in session:
        flash('You are required to login to access the app.', 'error')
        return redirect(url_for('customer.login'))
    
    # Get pizzas with ingredients eagerly loaded
    from sqlalchemy.orm import joinedload
    pizzas = Pizza.query.options(joinedload(Pizza.ingredients)).order_by(Pizza.pizza_id.asc()).all()
    
    # Prepare clean pizza data for template
    pizza_data = []
    for pizza in pizzas:
        # Check if pizza is vegetarian (all ingredients are vegetarian)
        is_vegetarian = True
        ingredient_names = []
        
        if pizza.ingredients:
            for ingredient in pizza.ingredients:
                ingredient_names.append(ingredient.name)
                if not ingredient.vegetarian:
                    is_vegetarian = False
        
        # Prepare ingredient display text
        if ingredient_names:
            if len(ingredient_names) <= 3:
                ingredients_text = ', '.join(ingredient_names)
            else:
                ingredients_text = ', '.join(ingredient_names[:3]) + ' and more...'
        else:
            ingredients_text = 'Delicious pizza with premium ingredients'
        
        pizza_info = {
            'pizza_id': pizza.pizza_id,
            'name': pizza.name,
            'price': pizza.price,
            'is_vegetarian': is_vegetarian,
            'ingredients_text': ingredients_text,
            'ingredient_count': len(ingredient_names) if ingredient_names else 0
        }
        pizza_data.append(pizza_info)
    
    customer = Customer.query.get(session['customer_id'])
    
    # Get customer's first name for welcome message
    customer_first_name = customer.first_name if customer else session.get('customer_name', '').split()[0]
    
    return render_template("customer_app.html", 
                         pizzas=pizza_data, 
                         customer=customer,
                         customer_first_name=customer_first_name)

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

# Update admin dashboard route
@admin_bp.route('/admin/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    admin_username = session.get('admin_username', 'Admin')
    
    stats = {
        'customers': Customer.query.count(),
        'pizzas': Pizza.query.count(),
        'ingredients': Ingredient.query.count(),
        'orders': Order.query.count(),
        'delivery_people': DeliveryPerson.query.count() if hasattr(globals(), 'DeliveryPerson') else 0,
        'discount_codes': DiscountType.query.count() if hasattr(globals(), 'DiscountType') else 0
    }
    
    recent_customers = Customer.query.order_by(Customer.customer_id.desc()).limit(5).all()
    
    return render_template("admin_dashboard.html", 
                         stats=stats, 
                         recent_customers=recent_customers,
                         admin_username=admin_username)

################ LOGOUT BUTTON ############
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
    
    stats = {
        'total_customers': len(customers),
        'customers_with_orders': len([c for c in customers if hasattr(c, 'orders') and c.orders]),
        'total_count': len(customers)  # For search functionality
    }
    
    return render_template("admin_customers.html", customers=customers, stats=stats)

# --------------------PIZZA ADMIN-----------------------------------
@admin_bp.route('/admin/pizzas')
def pizzas():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))

    pizzas = Pizza.query.options(joinedload(Pizza.ingredients)).order_by(Pizza.pizza_id.asc()).all()
    
    pizza_ingredients_query = db.session.query(
        pizza_ingredient.c.pizza_id,
        Ingredient.ingredient_id,
        Ingredient.name,
        Ingredient.vegetarian
    ).join(
        Ingredient, pizza_ingredient.c.ingredient_id == Ingredient.ingredient_id
    ).order_by(pizza_ingredient.c.pizza_id, Ingredient.name).all()
    
    # Group ingredients by pizza_id for easy lookup
    ingredients_by_pizza = {}
    for pizza_id, ingredient_id, ingredient_name, is_vegetarian in pizza_ingredients_query:
        if pizza_id not in ingredients_by_pizza:
            ingredients_by_pizza[pizza_id] = []
        ingredients_by_pizza[pizza_id].append({
            'id': ingredient_id,
            'name': ingredient_name,
            'vegetarian': is_vegetarian
        })
    
    # Prepare clean pizza data using the grouped ingredients
    pizza_data = []
    for pizza in pizzas:
        # Get ingredients from our pre-fetched data
        pizza_ingredients = ingredients_by_pizza.get(pizza.pizza_id, [])
        
        # Check if pizza is vegetarian (all ingredients are vegetarian)
        is_vegetarian = True
        ingredient_names = []
        
        for ingredient_info in pizza_ingredients:
            ingredient_names.append(ingredient_info['name'])
            if not ingredient_info['vegetarian']:
                is_vegetarian = False
        
        total_ingredient_cost = sum(float(ingredient.cost) for ingredient in pizza.ingredients) if pizza.ingredients else 0
        
        pizza_info = {
            'pizza_id': pizza.pizza_id,
            'name': pizza.name,
            'price': float(pizza.price),
            'description': pizza.description,
            'is_vegetarian': is_vegetarian,
            'ingredient_names': ingredient_names,
            'ingredient_count': len(ingredient_names),
            'total_ingredient_cost': total_ingredient_cost,
            'profit_margin': float(pizza.price) - total_ingredient_cost if total_ingredient_cost > 0 else 0
        }
        pizza_data.append(pizza_info)
    
    total_pizzas = len(pizza_data)
    vegetarian_pizzas = len([p for p in pizza_data if p['is_vegetarian']])
    non_vegetarian_pizzas = total_pizzas - vegetarian_pizzas
    avg_price = sum(p['price'] for p in pizza_data) / total_pizzas if total_pizzas > 0 else 0
    
    stats = {
        'total_pizzas': len(pizza_data),
        'vegetarian_pizzas': vegetarian_pizzas,
        'non_vegetarian_pizzas': total_pizzas - vegetarian_pizzas,
        'average_price': avg_price
    }
    
    return render_template("admin_pizzas.html", pizzas=pizza_data, stats=stats)

# ---------------------------------------------------------------------#

#--------------------INGREDIENTS ADMIN ----------------------------------
@admin_bp.route('/admin/ingredients')
def ingredients():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    ingredients = Ingredient.query.options(joinedload(Ingredient.pizzas)).order_by(Ingredient.ingredient_id.asc()).all()
    
    ingredient_data = []
    total_vegetarian = 0
    total_cost = 0
    
    for ingredient in ingredients:
        pizza_names = [pizza.name for pizza in ingredient.pizzas] if ingredient.pizzas else []
        pizza_count = len(pizza_names)
        
        if ingredient.vegetarian:
            total_vegetarian += 1
            
        total_cost += ingredient.cost
        
        ingredient_info = {
            'ingredient_id': ingredient.ingredient_id,
            'name': ingredient.name,
            'cost': ingredient.cost,
            'vegetarian': ingredient.vegetarian,
            'pizza_names': pizza_names[:2],  # Only first 2 for display
            'pizza_count': pizza_count,
            'has_more_pizzas': pizza_count > 2,
            'additional_pizzas': pizza_count - 2 if pizza_count > 2 else 0
        }
        ingredient_data.append(ingredient_info)
    
    total_ingredients = len(ingredient_data)
    total_non_vegetarian = total_ingredients - total_vegetarian
    
    stats = {
        'total_count': total_ingredients,
        'vegetarian_count': total_vegetarian,
        'non_vegetarian_count': total_non_vegetarian,
        'total_cost': total_cost
    }
    
    return render_template("admin_ingredients.html", ingredients=ingredient_data, stats=stats)

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
    
    orders = Order.query.order_by(Order.time_stamp.desc()).all()
    
    order_data = []
    total_revenue = 0
    delivered_count = 0
    
    for order in orders:
        customer = Customer.query.get(order.customer_id) if order.customer_id else None
        
        if customer:
            customer_name = f"{customer.first_name} {customer.last_name}"
            customer_email = customer.email
        else:
            customer_name = "Unknown Customer"
            customer_email = "No email"
        
        pizza_items = []
        if order.order_items:
            for order_item in order.order_items:
                pizza = Pizza.query.get(order_item.pizza_id) if order_item.pizza_id else None
                if pizza:
                    pizza_items.append({
                        'name': pizza.name,
                        'quantity': order_item.quantity
                    })
        
        if not pizza_items:
            pizza_items = [{'name': 'Pizza details not available', 'quantity': 1}]
        
        order_amount = float(order.total_price) if order.total_price else 0
        total_revenue += order_amount
        
        order_status = 'pending' 
        
        order_info = {
            'order_id': order.order_id,
            'order_date': order.time_stamp if order.time_stamp else datetime.now(),  # Using time_stamp
            'total_amount': order_amount,  # Using total_price from model
            'status': order_status,  # Default status
            'customer_name': customer_name,
            'customer_email': customer_email,
            'pizza_items': pizza_items
        }
        order_data.append(order_info)
    
    total_orders = len(order_data)
    average_order = total_revenue / total_orders if total_orders > 0 else 0
    
    stats = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'average_order': average_order,
        'delivered_orders': 0  # Since no status field exists, set to 0
    }
    
    return render_template("admin_orders.html", orders=order_data, stats=stats)

