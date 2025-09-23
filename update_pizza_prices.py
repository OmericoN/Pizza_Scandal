from app import create_app
from models import db, Pizza
from dotenv import load_dotenv
from decimal import Decimal, ROUND_UP

load_dotenv()

def nice_price(value):
    # round UP to the next 10-cent (0.10) boundary and return with two decimals
    d = Decimal(str(value))
    rounded_tenth = d.quantize(Decimal('0.1'), rounding=ROUND_UP)  # e.g. 6.56 -> 6.6
    return rounded_tenth.quantize(Decimal('0.01'))

def run_once_update_prices():
    app = create_app()
    with app.app_context():
        pizzas = Pizza.query.all()
        if not pizzas:
            print("No pizzas found.")
            return
        for p in pizzas:
            try:
                old_price = p.price
                # compute price from ingredients here instead of calling the model method
                base_cost = sum(float(ing.cost) for ing in p.ingredients)
                margin = 0.4
                vat = 0.09
                calculated = base_cost * (1 + margin) * (1 + vat)
                p.price = nice_price(calculated)
                print(f"Updated pizza {p.pizza_id} '{p.name}': {old_price} -> {p.price}")
            except Exception as e:
                print(f"Failed to update pizza {getattr(p, 'pizza_id', '?')} '{getattr(p, 'name', '?')}': {e}")
        db.session.commit()
        print("All done.")

if __name__ == "__main__":
    run_once_update_prices()