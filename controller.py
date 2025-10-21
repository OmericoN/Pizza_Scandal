from flask import Blueprint, app, render_template, request, redirect, url_for, flash, session
from models import db, Customer, Order, OrderItem, DeliveryPerson, DiscountCode, DiscountType, Admin, Pizza, pizza_ingredient, Ingredient, DeliveryPersonPostalRange
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import os
from datetime import datetime, timedelta, timezone, date
from sqlalchemy.orm import joinedload
from zoneinfo import ZoneInfo


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


#-------------------------Choose the right delivery person with cooldown------------------------------------------------------------
'''
This is a helper method to assign delivery persons based on the postal code 
'''
def _choose_delivery_person_for_zip(postal_code):
    """
    This is a helper method to assign delivery persons based on the postal code 
    """
    try:
        pc = int(str(postal_code).strip())
    except (TypeError, ValueError):
        pc = None

    cooldown_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    # First, try to find a delivery person for the specific postal code
    if pc is not None:
        dp = (DeliveryPerson.query
              .join(DeliveryPersonPostalRange,
                    DeliveryPersonPostalRange.delivery_person_id == DeliveryPerson.delivery_person_id)
              .filter(
                  DeliveryPersonPostalRange.start_zip <= pc,
                  DeliveryPersonPostalRange.end_zip >= pc
              )
              .filter(
                  (DeliveryPerson.last_assigned_at.is_(None)) |
                  (DeliveryPerson.last_assigned_at <= cooldown_threshold)
              )
              .order_by(func.random())
              .first())
        
        if dp:
            print(f"✅ Found delivery person {dp.name} for postal code {pc}")
            return dp
        else:
            print(f"⚠️ No delivery person found for postal code {pc} (checking cooldown)")
    
    # If no delivery person found for postal code, assign ANY available delivery person
    dp = (DeliveryPerson.query
          .filter(
              (DeliveryPerson.last_assigned_at.is_(None)) |
              (DeliveryPerson.last_assigned_at <= cooldown_threshold)
          )
          .order_by(func.random())
          .first())
    
    if dp:
        print(f"✅ Assigned fallback delivery person: {dp.name}")
        return dp
    
    # If all delivery persons are on cooldown, assign one anyway (oldest assignment)
    dp = (DeliveryPerson.query
          .order_by(DeliveryPerson.last_assigned_at.asc().nullsfirst())
          .first())
    
    if dp:
        print(f"⚠️ All delivery persons busy - assigned {dp.name} (cooldown override)")
        return dp
    
    print("❌ No delivery persons found in database!")
    return None

#-------------------------------



#This is the registration route for customers 
@customer_bp.route('/customer/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        gender = request.form.get('gender')
        dob = request.form.get('dob')  
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([first_name, last_name, email, telephone, address, postal_code, gender, dob, password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template("customer_register.html")
        
        gender_map = {
            'male': 0,
            'female': 1,
            'other': 2
        }
        
        if gender not in gender_map:
            flash('Please select a valid gender.', 'error')
            return render_template("customer_register.html")
        
        gender_int = gender_map[gender]
        
        try:
            postal_code_int = int(postal_code)
            if postal_code_int < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash('Please enter a valid postal code (numbers only).', 'error')
            return render_template("customer_register.html")
        
        # Validate and parse date of birth
        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
            
            # Check if customer is at least 13 years old
            today = date.today()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            
            if age < 13:
                flash('You must be at least 13 years old to register.', 'error')
                return render_template("customer_register.html")
            
            if dob_date > today:
                flash('Date of birth cannot be in the future.', 'error')
                return render_template("customer_register.html")
                
        except ValueError:
            flash('Please enter a valid date of birth.', 'error')
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
            peppered_password = password + PEPPER
            password_hash = generate_password_hash(peppered_password)
            
            new_customer = Customer(
                first_name=first_name,
                last_name=last_name,
                email=email,
                telephone=telephone,
                address=address,
                postal_code=postal_code_int,
                gender=gender_int,
                dob=dob_date,
                password_hash=password_hash
            )
            
            db.session.add(new_customer)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('customer.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template("customer_register.html")
    
    return render_template("customer_register.html")


# ThIs is the login route for customers 
@customer_bp.route('/customer/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template("customer_login.html")
        
        customer = Customer.query.filter_by(email=email).first()
        
        if customer and verify_password_with_pepper(password, customer.password_hash):
            session['customer_id'] = customer.customer_id
            session['customer_email'] = customer.email
            session['customer_name'] = f"{customer.first_name} {customer.last_name}"
            flash('Login successful! Welcome back!', 'success')
            return redirect(url_for('customer.app'))  
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template("customer_login.html")

#This is the logout route for customers
@customer_bp.route('/customer/logout')
def logout():
    session.pop('customer_id', None)
    session.pop('customer_email', None)
    session.pop('customer_name', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main.index'))


'''
This is a helper method, helping for the checkout trasnaction. It calculates the pizza price 
Based on the ingredients
'''
def compute_pizza_price(pizza):
    """Calculate pizza price based on ingredients + 40% margin + 9% VAT"""
    pizza_ingredients = db.session.query(
        Ingredient.ingredient_id,
        Ingredient.name,
        Ingredient.cost
    ).join(
        pizza_ingredient,
        pizza_ingredient.c.ingredient_id == Ingredient.ingredient_id
    ).filter(
        pizza_ingredient.c.pizza_id == pizza.pizza_id
    ).all()

    base_cost = sum(float(ing.cost) for ing in pizza_ingredients) 
    
    price_with_margin = base_cost * 1.40
    
    final_price = price_with_margin * 1.09
    
    return round(final_price, 1)


#App route for the customers
@customer_bp.route('/customer/app')
def app():
    if 'customer_id' not in session:
        flash('You are required to login to access the app.', 'error')
        return redirect(url_for('customer.login'))
    
    pizzas = Pizza.query.options(joinedload(Pizza.ingredients)).order_by(Pizza.pizza_id.asc()).all()
    
    pizza_data = []
    for pizza in pizzas:
        is_vegetarian = True
        ingredient_names = []
        
        if pizza.ingredients:
            for ingredient in pizza.ingredients:
                ingredient_names.append(ingredient.name)
                if not ingredient.vegetarian:
                    is_vegetarian = False
        
        if ingredient_names:
            if len(ingredient_names) <= 3:
                ingredients_text = ', '.join(ingredient_names)
            else:
                ingredients_text = ', '.join(ingredient_names[:3]) + ' and more...'
        else:
            ingredients_text = 'Delicious pizza with premium ingredients'
        
        dynamic_price = compute_pizza_price(pizza)
        
        pizza_info = {
            'pizza_id': pizza.pizza_id,
            'name': pizza.name,
            'price': dynamic_price, 
            'is_vegetarian': is_vegetarian,
            'ingredients_text': ingredients_text,
            'ingredient_count': len(ingredient_names) if ingredient_names else 0
        }
        pizza_data.append(pizza_info)
    
    customer = Customer.query.get(session['customer_id'])
    
    customer_first_name = customer.first_name if customer else session.get('customer_name', '').split()[0]
    
    return render_template("customer_app.html", 
                         pizzas=pizza_data, 
                         customer=customer,
                         customer_first_name=customer_first_name)



# This is the route that handles the checkout when paying
@customer_bp.route("/customer/app/checkout", methods=['GET', 'POST'])
def checkout():
    if 'customer_id' not in session:
        return redirect(url_for('customer.login'))
    
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('customer.app'))
    
    customer = Customer.query.get(session['customer_id'])
    
    cart_items = []
    total_with_vat = 0
    total_pizza_count = 0  # ✅ Initialize
    
    for pizza_id, item in cart.items():
        subtotal = item['price'] * item['quantity']
        total_with_vat += subtotal
        total_pizza_count += item['quantity']  # ✅ COUNT PIZZAS HERE
        
        cart_items.append({
            'pizza_id': pizza_id,
            'name': item['name'],
            'quantity': item['quantity'],
            'subtotal': subtotal,
            'is_vegetarian': item['is_vegetarian']
        })
    
    subtotal_without_vat = total_with_vat / 1.09
    vat_amount = total_with_vat - subtotal_without_vat
    
    if request.method == 'POST':
        delivery_address = request.form.get('delivery_address', customer.address)
        notes = request.form.get('notes', '')
        discount_code_input = request.form.get('discount_code', '').strip().upper()
        
        dp = _choose_delivery_person_for_zip(customer.postal_code if customer else None)
        
        try:
            # Initialize discount variables
            final_total = total_with_vat
            applied_discount_code_id = None
            discount_was_applied = False
            pizzas_added_to_loyalty = False  # ✅ Track if pizzas were added
            
            # === DISCOUNT CODE VALIDATION ===
            if discount_code_input:
                is_eligible, message, discount_type, birthday_discount_amount = check_discount_eligibility(
                    session['customer_id'], 
                    discount_code_input, 
                    cart
                )
                
                if is_eligible and discount_type:
                    # Calculate discount based on type
                    if discount_type.name == "Birthday Discount":
                        discount_amount = float(birthday_discount_amount)
                    else:
                        discount_percent = float(discount_type.percent)
                        discount_amount = total_with_vat * (discount_percent / 100)
                    
                    final_total = total_with_vat - discount_amount
                    
                    # Get the discount code ID from database
                    code_obj = DiscountCode.query.filter_by(code=discount_code_input).first()
                    if code_obj:
                        applied_discount_code_id = code_obj.discount_code_id
                        discount_was_applied = True
                        flash(f"✅ {message} - You saved ${discount_amount:.2f}!", "success")
                    else:
                        flash("Error: Could not apply discount code", "error")
                    
                    # ✅ FIXED: Handle loyalty discount pizza count
                    if discount_type.name == "Loyalty Reward":
                        # Customer used 10 pizzas for discount
                        pizzas_used_for_discount = 10
                        remaining_pizzas = total_pizza_count - pizzas_used_for_discount
                        
                        if remaining_pizzas > 0:
                            # Reset to 0 and add remaining pizzas from this order
                            customer.loyalty_pizza_count = remaining_pizzas
                        else:
                            # Reset to 0
                            customer.loyalty_pizza_count = 0
                        
                        pizzas_added_to_loyalty = True
                        print(f"✅ Loyalty discount used. Pizza count reset to {customer.loyalty_pizza_count}")
                    else:
                        # Other discounts (WELCOME20, Birthday): add all pizzas
                        customer.add_pizzas_to_count(total_pizza_count)
                        pizzas_added_to_loyalty = True
                        print(f"✅ Added {total_pizza_count} pizzas. New loyalty count: {customer.loyalty_pizza_count}")
                else:
                    # Discount code invalid - still add pizzas to loyalty
                    flash(f"❌ {message}", "error")
                    customer.add_pizzas_to_count(total_pizza_count)
                    pizzas_added_to_loyalty = True
                    print(f"✅ Discount failed. Added {total_pizza_count} pizzas. New count: {customer.loyalty_pizza_count}")
            else:
                # No discount code - add pizzas to loyalty
                customer.add_pizzas_to_count(total_pizza_count)
                pizzas_added_to_loyalty = True
                print(f"✅ No discount code. Added {total_pizza_count} pizzas. New count: {customer.loyalty_pizza_count}")
            
            # ✅ Safety net: Ensure pizzas are always counted
            if not pizzas_added_to_loyalty:
                customer.add_pizzas_to_count(total_pizza_count)
                print(f"⚠️ Safety net triggered. Added {total_pizza_count} pizzas. Count: {customer.loyalty_pizza_count}")
            
            # Create the order
            new_order = Order(
                customer_id=session['customer_id'],
                delivery_person_id=(dp.delivery_person_id if dp else None),
                total_price=final_total,
                discount_code_id=applied_discount_code_id,
                time_stamp=datetime.now(timezone.utc)
            )
            
            db.session.add(new_order)
            db.session.flush()
            
            print(f"✅ Order created: order_id={new_order.order_id}, discount_code_id={new_order.discount_code_id}, total={new_order.total_price}")
            
            # Create order items
            for pizza_id, item in cart.items():
                order_item = OrderItem(
                    order_id=new_order.order_id,
                    pizza_id=int(pizza_id),
                    quantity=item['quantity'],
                    unit_price=item['price']
                )
                db.session.add(order_item)
            
            # Update delivery person
            if dp:
                dp.last_assigned_at = datetime.now(timezone.utc)
                db.session.add(dp)
            
            # ✅ Commit everything together (including loyalty count update)
            db.session.commit()
            
            # Verify
            saved_order = Order.query.get(new_order.order_id)
            refreshed_customer = Customer.query.get(customer.customer_id)
            print(f"✅ Verified: discount_code_id={saved_order.discount_code_id}")
            print(f"✅ Final loyalty pizza count: {refreshed_customer.loyalty_pizza_count}")
            
            # Clear cart
            session.pop('cart', None)
            
            flash('🎉 Order placed successfully!', 'success')
            return redirect(url_for('customer.order_confirmation', order_id=new_order.order_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error processing order: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error processing order: {str(e)}', 'error')
            return redirect(url_for('customer.checkout'))
    
    return render_template('customer_checkout.html',
                         customer=customer,
                         cart_items=cart_items,
                         total=total_with_vat,
                         subtotal=subtotal_without_vat,
                         vat_amount=vat_amount,
                         vat_rate=9)

# Here the customers can see the order confirmation
@customer_bp.route('/customer/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer.login'))
    
    order = Order.query.get_or_404(order_id)
    
    if order.customer_id != session['customer_id']:
        flash("Access denied: Order not found", "error")
        return redirect(url_for('customer.app'))
    
    order_items = []
    for item in order.order_items:
        pizza = Pizza.query.get(item.pizza_id)
        if pizza:
            order_items.append({
                'name': pizza.name,
                'quantity': item.quantity,
                'price': float(item.unit_price),  
                'subtotal': float(item.unit_price) * item.quantity
            })
    
    customer = Customer.query.get(session['customer_id'])
    
    subtotal_without_vat = float(order.total_price) / 1.09
    vat_amount = float(order.total_price) - subtotal_without_vat
    
    return render_template('customer_order_confirmation.html',
                         order=order,
                         order_items=order_items,
                         customer=customer,
                         subtotal_without_vat=subtotal_without_vat,
                         vat_amount=vat_amount)

# Here the customers can see their orders 
@customer_bp.route('/customer/orders')
def customer_orders():
   if 'customer_id' not in session:
       flash('Please log in first.', 'error')
       return redirect(url_for('customer.login'))
  
   orders = Order.query.filter_by(customer_id=session['customer_id']).order_by(Order.time_stamp.desc()).all()
  
   order_list = []
   for order in orders:
       order_info = {
           'order_id': order.order_id,
           'total_price': float(order.total_price),
           'time_stamp': order.time_stamp,
           'status': order.get_status(),  
           'delivery_person': order.delivery_person.name if order.delivery_person else 'Assigning...',
           'delivered_at': order.delivered_at
       }
       order_list.append(order_info)
  
   return render_template('customer_orders.html', orders=order_list)

# Adding stuff to the cart
@customer_bp.route('/customer/cart/add', methods=['POST'])
def add_to_cart():
    if 'customer_id' not in session:
        return redirect(url_for('customer.login'))
    
    pizza_id = request.form.get('pizza_id')
    quantity = int(request.form.get('quantity', 1))
    
    if quantity <= 0:
        flash('Please select a valid quantity', 'error')
        return redirect(url_for('customer.app'))
    
    pizza = Pizza.query.get_or_404(pizza_id)
    
    dynamic_price = compute_pizza_price(pizza)

    
    is_vegetarian = True
    for ingredient in pizza.ingredients:
        if not ingredient.vegetarian:
            is_vegetarian = False
            break
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    if pizza_id in cart:
        cart[pizza_id]['quantity'] += quantity
    else:
        cart[pizza_id] = {
            'name': pizza.name,
            'price': dynamic_price,  
            'quantity': quantity,
            'is_vegetarian': is_vegetarian
        }
    
    session['cart'] = cart
    flash(f'Added {quantity} {pizza.name} to cart!', 'success')
    return redirect(url_for('customer.app'))

# This makes sure that the customers can see theit cart
@customer_bp.route('/customer/cart')
def view_cart():
    if 'customer_id' not in session:
        return redirect(url_for('customer.login'))
    
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    
    for pizza_id, item in cart.items():
        subtotal = item['price'] * item['quantity']
        total += subtotal
        cart_items.append({
            'pizza_id': pizza_id,
            'name': item['name'],
            'price': item['price'],
            'quantity': item['quantity'],
            'subtotal': subtotal,
            'is_vegetarian': item['is_vegetarian']
        })
    
    return render_template('customer_cart.html', 
                         cart_items=cart_items, 
                         total=total)

# Route that allows to remove stuff from the cart
@customer_bp.route('/customer/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'customer_id' not in session:
        return redirect(url_for('customer.login'))
    
    pizza_id = request.form.get('pizza_id')
    cart = session.get('cart', {})
    
    if pizza_id in cart:
        del cart[pizza_id]
        session['cart'] = cart
        flash('Item removed from cart', 'success')
    
    return redirect(url_for('customer.view_cart'))

# Enable to clear the whole cart
@customer_bp.route('/customer/cart/clear', methods=['POST'])
def clear_cart():
    if 'customer_id' not in session:
        return redirect(url_for('customer.login'))
    
    session.pop('cart', None)
    flash('Cart cleared', 'success')
    return redirect(url_for('customer.app'))




@main_bp.route("/menu")
def menu():
    pizzas = Pizza.query.all()
    return {"pizzas": [pizza.name for pizza in pizzas]}





######## BELOW IS THE CONTROLLER FOR THE ADMIN DASHBOARD, THIS CAN ONLY BE ACCESSED USING AN ADMIN ACCOUNT

#---------------------ADMIN DASHBOARD ---------------------------------
#Admin login
@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and verify_password_with_pepper(password, admin.password_hash):
            session['admin_id'] = admin.admin_id
            session['admin_username'] = admin.username
            flash('Login successful!', 'success')
            return redirect(url_for('admin.dashboard'))  
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template("admin_login.html")

# The admin dashboard
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
        'delivery_people': DeliveryPerson.query.count(),  # ✅ FIXED: Remove the hasattr check
        'discount_codes': DiscountType.query.count()  # ✅ FIXED: Remove the hasattr check
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
@admin_bp.route('/admin/customers')
def customers():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    customers = Customer.query.order_by(Customer.customer_id.asc()).all()
    
    stats = {
        'total_customers': len(customers),
        'customers_with_orders': len([c for c in customers if hasattr(c, 'orders') and c.orders]),
        'total_count': len(customers) 
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
    
    ingredients_by_pizza = {}
    for pizza_id, ingredient_id, ingredient_name, is_vegetarian in pizza_ingredients_query:
        if pizza_id not in ingredients_by_pizza:
            ingredients_by_pizza[pizza_id] = []
        ingredients_by_pizza[pizza_id].append({
            'id': ingredient_id,
            'name': ingredient_name,
            'vegetarian': is_vegetarian
        })
    
    pizza_data = []
    for pizza in pizzas:
        pizza_ingredients = ingredients_by_pizza.get(pizza.pizza_id, [])
        
        is_vegetarian = True
        ingredient_names = []
        
        for ingredient_info in pizza_ingredients:
            ingredient_names.append(ingredient_info['name'])
            if not ingredient_info['vegetarian']:
                is_vegetarian = False
        
        total_ingredient_cost = sum(float(ingredient.cost) for ingredient in pizza.ingredients) if pizza.ingredients else 0
        
        dynamic_price = compute_pizza_price(pizza)
        
        pizza_info = {
            'pizza_id': pizza.pizza_id,
            'name': pizza.name,
            'price': dynamic_price,  
            'description': pizza.description,
            'is_vegetarian': is_vegetarian,
            'ingredient_names': ingredient_names,
            'ingredient_count': len(ingredient_names),
            'total_ingredient_cost': total_ingredient_cost,
            'profit_margin': dynamic_price - total_ingredient_cost if total_ingredient_cost > 0 else 0
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
            'pizza_names': pizza_names[:2],  
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
            'order_date': order.time_stamp if order.time_stamp else datetime.now(),  
            'total_amount': order_amount,  
            'status': order_status,  
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
        'delivered_orders': 0  
    }
    
    return render_template("admin_orders.html", orders=order_data, stats=stats)

#-------------------- ADMIN REPORTS ------------------------------------------------------------------------------------------
@admin_bp.route('/admin/reports/undelivered')
def undelivered_orders():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    undelivered = Order.query.filter(
        Order.status.in_(['pending', 'preparing', 'out_for_delivery'])
    ).order_by(Order.time_stamp.desc()).all()
    
    report_data = []
    for order in undelivered:
        customer = Customer.query.get(order.customer_id)
        delivery_person = DeliveryPerson.query.get(order.delivery_person_id) if order.delivery_person_id else None
        
        report_data.append({
            'order_id': order.order_id,
            'customer_name': f"{customer.first_name} {customer.last_name}",
            'customer_address': customer.address,
            'customer_postal_code': customer.postal_code,
            'status': order.get_status(),
            'order_time': order.time_stamp,
            'delivery_person': delivery_person.name if delivery_person else 'Not assigned',
            'total': float(order.total_price)
        })
    
    return render_template('admin_reports_undelivered.html', orders=report_data)

@admin_bp.route('/admin/reports/top-pizzas')
def top_pizzas():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    top_pizzas_query = (
        db.session.query(
            Pizza.pizza_id,
            Pizza.name,
            func.sum(OrderItem.quantity).label('total_sold'),
            func.count(func.distinct(Order.order_id)).label('order_count')
        )
        .join(OrderItem, OrderItem.pizza_id == Pizza.pizza_id)
        .join(Order, Order.order_id == OrderItem.order_id)
        .filter(Order.time_stamp >= one_month_ago)
        .group_by(Pizza.pizza_id, Pizza.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(3)
        .all()
    )
    
    report_data = []
    for pizza_id, name, total_sold, order_count in top_pizzas_query:
        pizza = Pizza.query.get(pizza_id)
        price = compute_pizza_price(pizza)  
        revenue = float(total_sold) * price
        
        report_data.append({
            'rank': len(report_data) + 1,
            'name': name,
            'total_sold': int(total_sold),
            'order_count': int(order_count),
            'price': price,
            'revenue': revenue
        })
    
    return render_template('admin_reports_top_pizzas.html', pizzas=report_data)


@admin_bp.route('/admin/reports/earnings')
def earnings_report():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    filter_type = request.args.get('filter', 'gender')
    
    if filter_type == 'gender':
        gender_earnings = (
            db.session.query(
                Customer.gender,
                func.count(Order.order_id).label('order_count'),
                func.sum(Order.total_price).label('total_revenue')
            )
            .join(Order, Order.customer_id == Customer.customer_id)
            .group_by(Customer.gender)
            .all()
        )
        
        report_data = []
        for gender, order_count, total_revenue in gender_earnings:
            report_data.append({
                'category': gender.capitalize() if gender else 'Unknown',
                'order_count': int(order_count),
                'total_revenue': float(total_revenue) if total_revenue else 0,
                'avg_order_value': float(total_revenue / order_count) if order_count > 0 else 0
            })
    
    # ===== BY AGE GROUP - SKIP FOR NOW (no date_of_birth yet) =====
    elif filter_type == 'age':
        from datetime import date as _date

        customers_with_orders = (
            db.session.query(
                Customer.customer_id,
                Customer.dob,
                func.sum(Order.total_price).label('total_revenue'),
                func.count(Order.order_id).label('order_count')
            )
            .join(Order, Order.customer_id == Customer.customer_id)
            .filter(Customer.dob.isnot(None))
            .group_by(Customer.customer_id, Customer.dob)
            .all()
        )

        age_groups = {
            '18-25': {'revenue': 0.0, 'orders': 0},
            '26-35': {'revenue': 0.0, 'orders': 0},
            '36-50': {'revenue': 0.0, 'orders': 0},
            '51+':   {'revenue': 0.0, 'orders': 0}
        }

        today = date.today()
        for customer_id, dob, revenue, orders in customers_with_orders:
            if not dob:
                continue
            try:
                age = today.year - dob.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            except Exception:
                continue

            rev = float(revenue) if revenue else 0.0
            ords = int(orders) if orders else 0

            if 18 <= age <= 25:
                bucket = '18-25'
            elif 26 <= age <= 35:
                bucket = '26-35'
            elif 36 <= age <= 50:
                bucket = '36-50'
            else:
                bucket = '51+'

            age_groups[bucket]['revenue'] += rev
            age_groups[bucket]['orders'] += ords

        report_data = []
        for age_range, data in age_groups.items():
            report_data.append({
                'category': age_range,
                'order_count': data['orders'],
                'total_revenue': data['revenue'],
                'avg_order_value': (data['revenue'] / data['orders']) if data['orders'] > 0 else 0
            })
    
    elif filter_type == 'postal_code':
        postal_earnings = (
            db.session.query(
                Customer.postal_code,
                func.count(Order.order_id).label('order_count'),
                func.sum(Order.total_price).label('total_revenue')
            )
            .join(Order, Order.customer_id == Customer.customer_id)
            .filter(Customer.postal_code.isnot(None))  
            .group_by(Customer.postal_code)
            .order_by(func.sum(Order.total_price).desc())
            .limit(20)  
            .all()
        )
        
        report_data = []
        for postal_code, order_count, total_revenue in postal_earnings:
            report_data.append({
                'category': f'Postal Code {postal_code}',
                'order_count': int(order_count),
                'total_revenue': float(total_revenue) if total_revenue else 0,
                'avg_order_value': float(total_revenue / order_count) if order_count > 0 else 0
            })
    
    else:
        report_data = []
    
    return render_template('admin_reports_earnings.html', 
                         report_data=report_data, 
                         filter_type=filter_type)

def check_discount_eligibility(customer_id, discount_code, cart):
    """
    Check if customer is eligible for a discount code.
    Returns: (is_eligible: bool, message: str, discount_type: DiscountType or None, discount_amount: float)
    """
    if not customer_id or not discount_code:
        return False, "Invalid request", None, 0
    
    code = DiscountCode.query.filter_by(code=discount_code.upper().strip()).first()
    if not code:
        return False, f"Discount code '{discount_code}' does not exist", None, 0
    
    discount_type = DiscountType.query.get(code.discount_type_id)
    if not discount_type:
        return False, "Discount type configuration error", None, 0
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return False, "Customer not found", None, 0
    
    if discount_type.name == "One-Time Promo":
        orders_with_this_code = (
            db.session.query(Order)
            .filter(
                Order.customer_id == customer_id,
                Order.discount_code_id == code.discount_code_id
            )
            .all() 
        )
        
        if orders_with_this_code:
            order_count = len(orders_with_this_code)
            return False, f"This one-time discount code has already been used by you ({order_count} time(s)). Each customer can only use WELCOME20 once.", None, 0
        
        return True, f"One-Time Promo: {discount_type.percent}% off your order", discount_type, 0
    
    elif discount_type.name == "Birthday Discount":
        if not customer.is_birthday_today():
            return False, f"Birthday discount only works on your birthday ({customer.dob.strftime('%B %d')}). Come back then!", None, 0
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        birthday_orders_today = (
            db.session.query(Order)
            .filter(
                Order.customer_id == customer_id,
                Order.discount_code_id == code.discount_code_id,
                Order.time_stamp >= today_start,
                Order.time_stamp <= today_end
            )
            .all()
        )
        
        if birthday_orders_today:
            return False, "You have already used your birthday discount today. Only one birthday discount per year!", None, 0
        
        if not cart:
            return False, "Your cart is empty", None, 0
        
        cheapest_pizza_price = min(item['price'] for item in cart.values())
        
        return True, f"🎂 Happy Birthday! 1 FREE cheapest pizza (worth ${cheapest_pizza_price:.2f})", discount_type, cheapest_pizza_price
    
    elif discount_type.name == "Loyalty Reward":
        cart_pizza_count = sum(item['quantity'] for item in cart.values())
        
        total_pizzas = customer.loyalty_pizza_count + cart_pizza_count
        
        if total_pizzas < 10:
            pizzas_needed = 10 - customer.loyalty_pizza_count
            return False, f"You need {pizzas_needed} more pizza(s) to unlock the loyalty discount. You currently have {customer.loyalty_pizza_count} pizzas in your loyalty count.", None, 0
        
        return True, f"🎉 Loyalty Reward: {discount_type.percent}% off! (You've earned this with {customer.loyalty_pizza_count} pizzas)", discount_type, 0
    
    return False, "Unknown discount type", None, 0


@customer_bp.route('/customer/validate-discount', methods=['POST'])
def validate_discount():
    """AJAX endpoint to validate discount code before checkout"""
    if 'customer_id' not in session:
        return {'valid': False, 'message': 'Please log in first'}, 401
    
    discount_code = request.json.get('discount_code', '').strip().upper()
    cart = session.get('cart', {})
    
    if not discount_code:
        return {'valid': False, 'message': 'Please enter a discount code'}, 400
    
    if not cart:
        return {'valid': False, 'message': 'Your cart is empty'}, 400
    
    total_with_vat = sum(item['price'] * item['quantity'] for item in cart.values())
    
    is_eligible, message, discount_type, birthday_discount_amount = check_discount_eligibility(
        session['customer_id'],
        discount_code,
        cart
    )
    
    if not is_eligible:
        return {
            'valid': False,
            'message': message
        }, 400
    
    if discount_type.name == "Birthday Discount":
        discount_amount = birthday_discount_amount
        discount_percent = "FREE Pizza"
    else:
        discount_percent = float(discount_type.percent)
        discount_amount = total_with_vat * (discount_percent / 100)
    
    new_total = total_with_vat - discount_amount
    new_subtotal = new_total / 1.09
    new_vat = new_total - new_subtotal
    
    return {
        'valid': True,
        'message': message,
        'discount_percent': discount_percent,
        'discount_amount': round(discount_amount, 2),
        'original_total': round(total_with_vat, 2),
        'new_total': round(new_total, 2),
        'new_subtotal': round(new_subtotal, 2),
        'new_vat': round(new_vat, 2),
        'savings': round(discount_amount, 2)
    }, 200