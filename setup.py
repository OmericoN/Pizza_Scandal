from sqlalchemy import create_engine
from getpass import getpass

password = getpass("Enter DB password: ")
engine = create_engine(f'mysql+pymysql://root:{password}@localhost/pizza_ordering', echo=True)

try:
    with engine.connect() as conn:
        print("Connection to the database was successful!")
except Exception as e:
    print(f"An error occurred: {e}")