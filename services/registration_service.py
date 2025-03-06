import random
import string
from sqlalchemy.exc import IntegrityError
from models import db, User, Package, CommissionConfig, Referral
from datetime import datetime, timezone



def generate_unique_referral_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        random.shuffle(list(code))
        shuffled_code = ''.join(code)
        if not User.query.filter_by(referral_code=shuffled_code).first():
            return shuffled_code
            
def calculate_commission(referrer: User, referred: User) -> float:
    # Ensure referred user has a valid package
    if not referred.package:
        return 0.0
    
    # Check if the referrer can refer this package
    if not referrer.can_refer(referred.package):
        return 0.0

    # Retrieve commission rate from the database
    commission_config = CommissionConfig.query.filter_by(category=referred.package.category).first()
    if not commission_config:
        return 0.0
    
    commission = referred.package.amount * commission_config.rate
    print("Commission: ", commission)
    referrer.income += commission
    db.session.commit()
    return commission


def register_user(name, phone, email, password_hash, username, package_id, referral_code=None):
    """Register a new user with optional referral logic and commission calculation."""
    try:
        # Get the selected package
        package = Package.query.get(package_id)
        if not package:
            return {'error': 'Invalid package selected'}
        
        # Generate a unique referral code for the new user
        new_referral_code = generate_unique_referral_code()

        # Create the new user
        new_user = User(
            name=name,
            phone=phone,
            email=email,
            password_hash=password_hash,
            username=username,
            created_at=datetime.now(timezone.utc),
            package_id=package_id,
            referral_code=new_referral_code
        )

        # Handle referral logic if referral code is provided
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                if referrer.can_refer(package):
                    # Assign referrer to the new user
                    new_user.referrer_id = referrer.id

                    # Create a referral record
                    referral_entry = Referral(
                        referrer_id=referrer.id,
                        referred=new_user,
                        status='pending'
                    )
                    db.session.add(referral_entry)
                else:
                    return {'error': 'Referrer is not eligible to refer at this package level'}
            else:
                return {'error': 'Invalid referral code'}
        
        # Commit the new user to the database
        db.session.add(new_user)
        db.session.commit()

        return {'success': f'User {name} registered successfully with referral code {new_referral_code}'}

    except IntegrityError:
        db.session.rollback()
        return {'error': 'Duplicate phone, email, or username detected'}

    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}
