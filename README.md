# Pizza_Scandal
Collaborated project done by Omer and Raul for the Databases course (University Maastricht)
## ORM setup
Install SQLAlchemy as the ORM `pip install SQLAlchemy`  
Install mysql driver for python `pip install pymysql`  

## How to use the app
**Create Virtual Environment**
`source .venv/bin/activate (mac)`

**Run python app.py**
`python app.py`

## Supabase 
We have added Mr. Pepels to our supabase database so you can have a look at it.
o.nidam@student.maastrichtuniversity.nl sent the corresponding email. 

## Features
 
### Customer Features
- User authentication (registration/login)
- Browse pizzas with dynamic pricing
- Shopping cart functionality
- Checkout with discount codes
- Real-time order tracking
- Order history
### Admin Features
- Dashboard with statistics
- Customer management
- Pizza & ingredient management
- Delivery person management
- Discount code management
- Order overview
### Delivery Assignment
- Postal code range-based assignment
- 30-minute cooldown per delivery person
- Fallback to random assignment
### Order Status Tracking
- **Pending** (0 min)
- **Preparing** (0-10 min)
- **Out for Delivery** (10-30 min)
- **Delivered** (30+ min)


## Tech Stack

**Backend:**
- Python 3.10+
- Flask (web framework)
- Flask-SQLAlchemy (ORM)
- Flask-Migrate (database migrations)
- Werkzeug (password hashing)

**Database:**
- Supabase (PostgreSQL)

**Frontend:**
- Jinja2 templates
- Custom CSS with design system
- Vanilla JavaScript

## Database Schema 

### Entitity Relationship Diagram

![ERD Diagram]()

## Project Structure

```
Pizza_Scandal/
├── app.py                 # Application entry point
├── models.py              # Database models
├── controller.py          # Route handlers
├── templates/             # Jinja2 templates
│   ├── layout_v2.html     # Base template
│   ├── customer_app.html  # Customer interface
│   ├── customer_orders.html
│   ├── admin_dashboard.html
│   └── ...
├── migrations/            # Database migrations
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── README.md
```

## API Endpoints

### Customer Routes (`/customer`)
- `GET /customer/register` - Registration page
- `POST /customer/register` - Create account
- `GET /customer/login` - Login page
- `POST /customer/login` - Authenticate
- `GET /customer/app` - Browse pizzas
- `POST /customer/add-to-cart` - Add pizza to cart
- `GET /customer/cart` - View cart
- `POST /customer/checkout` - Place order
- `GET /customer/orders` - Order history
- `GET /customer/order-confirmation/<id>` - Order details

### Admin Routes (`/admin`)
- `GET /admin/login` - Admin login
- `GET /admin/dashboard` - Statistics overview
- `GET /admin/customers` - Customer list
- `GET /admin/pizzas` - Pizza management
- `GET /admin/orders` - Order management
- `GET /admin/delivery-people` - Delivery person management
- `GET /admin/discount-codes` - Discount code management


## Key Implementation Details

### Dynamic Pizza Pricing
Pizza prices are calculated based on ingredient costs in real-time:
```python
def calculate_pizza_price(pizza):
    total = sum(ingredient.cost for ingredient in pizza.ingredients)
    return total
```

### Delivery Person Assignment
1. Query delivery persons covering customer's postal code
2. Filter out those assigned in last 30 minutes (cooldown)
3. Pick random from available
4. Fallback to random if none available

### Order Status Auto-Progression
Status updates automatically based on elapsed time:
- 0-10 min → `preparing`
- 10-30 min → `out_for_delivery`
- 30+ min → `delivered`