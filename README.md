# Pizza_Scandal
Collaborated project done by Omer and Raul for the Databases course (University Maastricht)
## ORM setup
Install SQLAlchemy as the ORM `pip install SQLAlchemy`  
Install mysql driver for python `pip install pymysql`  

## Database Distribution
Make sure to enter mysql commands using the Command Line (not shell) and configure the path
example (Omer's end): `C:\Users\omern\Documents\GitHub\Pizza_Scandal\schema>`

**For exporting database changes**
`mysqldump -u root -p pizza_ordering > pizza_ordering.sql`

**For importing database changes**
`mysql -u root -p pizza_ordering < pizza_ordering.sql`

-use SQLAlchemy as the ORM
-Use bcrypt to encrypt passwords 
-use salting techniques (change password bits) [salt is in the database]
-use pepper [pepper is stored in the application]