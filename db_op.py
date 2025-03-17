from models import db, User
from app import app
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from sqlalchemy import inspect


with app.app_context():
    # Fetch all users
    email = "amirkuje001@gmail.com"
    user = User.query.filter_by(email=email).first()
    #user.deposit = 500.0
    #db.session.commit()
    #print("User updated successfully!")

    print(user.id, user.name, user.username, user.email, user.deposit, user.earnings)



"""
with app.app_context():
    admin_email = "admin@pss.com"
    admin_password = "admin123"

    existing_admin = User.query.filter_by(email=admin_email).first()
    if not existing_admin:
        admin = User(
            name="Admin",
            phone="08012345678",
            username="admin",
            email=admin_email,
            package=None,
            referrer_id=None,
            referral_code="ADMIN",
            password_hash=generate_password_hash(admin_password),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user added to DataBase!")
    else:
        print("Admin already exists.")"""
    

# Check if the table already exists
"""with app.app_context():
    inspector = inspect(db.engine)
    if 'investments' not in inspector.get_table_names():
        db.session.execute(text('''
            CREATE TABLE investments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                deposit REAL NOT NULL DEFAULT 0.0,
                profit REAL NOT NULL DEFAULT 0.0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        '''))
        db.session.commit()
        print("Investments table created successfully!")
    else:
        print("Investments table already exists.")
"""


## Adding values for investments
"""from datetime import datetime
with app.app_context():
    investments = [
        Investment(user_id=2, category="MMF", deposit=25000.0, profit=0.0, created_at=datetime.now(timezone.utc)),
        Investment(user_id=2, category="REA", deposit=40000.0, profit=0.0, created_at=datetime.now(timezone.utc)),
        Investment(user_id=2, category="MCF", deposit=35000.0, profit=0.0, created_at=datetime.now(timezone.utc))
    ]

    db.session.add_all(investments)
    db.session.commit()"""
    
    
    
"""
with app.app_context():
    db.session.execute(text('DROP TABLE IF EXISTS investments;'))
    #db.session.commit()
    #db.session.execute(text('CREATE TABLE questions (id INTEGER PRIMARY KEY AUTOINCREMENT, question_text TEXT NOT NULL, option_a TEXT NOT NULL, option_b TEXT NOT NULL, option_c TEXT NOT NULL, option_d TEXT NOT NULL, correct_answer INTEGER NOT NULL, image TEXT);'))
    db.session.commit()"""












"""with app.app_context():
    db.session.execute(text('ALTER TABLE users MODIFY password_hash VARCHAR(255);'))
    db.session.commit()"""
