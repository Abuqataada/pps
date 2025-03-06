import random
import string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from flask_login import UserMixin


db = SQLAlchemy()

class Package(db.Model):
    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # Starter, Growth, Premium
    level = db.Column(db.Integer, nullable=False, unique=True)  # Helps with package hierarchy

    def __repr__(self):
        return f"<Package {self.name} - {self.category}>"


class AccountDetails(db.Model):
    __tablename__ = 'account_details'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(20), nullable=False, unique=True)
    account_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)

    user = relationship('User', back_populates='account_details')

    def __repr__(self):
        return f"<AccountDetails {self.bank_name} - {self.account_name}>"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(15), nullable=False)  # 'deposit' or 'withdrawal'
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id'))
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    earnings = db.Column(db.Float, default=0.0)   # Total income and commission from referral system
    income = db.Column(db.Float, default=0.0)   # Total percentage earn from direct deposit
    referral_code = db.Column(db.String(10), unique=True, nullable=False)
    deposit = db.Column(db.Float, default=0.0)   # Direct fund deposit
    total_withdrawable = db.Column(db.Float, default=0.0)   # Total money eligible for withdrawal

    package = relationship('Package', backref='users')
    referrer = relationship('User', remote_side=[id], backref='referrals')
    account_details = relationship('AccountDetails', uselist=False, back_populates='user')


    def can_refer(self, referred_package):
        # Users can only refer packages within their current category
        return referred_package.category == self.package.category

    def __repr__(self):
        return f"<User {self.name} - Package: {self.package.name}>"


# Referral model
class Referral(db.Model):
    __tablename__ = 'referrals'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    referrer_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    referred_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    commission = db.Column(db.Float, nullable=False, default='0.0')
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')  # pending, paid, failed

    referrer = relationship('User', foreign_keys=[referrer_id])
    referred = relationship('User', foreign_keys=[referred_id])

    def __repr__(self):
        return f"<Referral: Referrer={self.referrer_id}, Referred={self.referred_id}, Commission={self.commission}>"


class CommissionConfig(db.Model):
    __tablename__ = 'commission_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(20), unique=True, nullable=False)
    rate = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<CommissionConfig {self.category} - {self.rate}>"


def seed_packages():
    packages = [
        ("N500", 500, "Bronze", 1),
        ("N1k", 1000, "Bronze", 2),
        ("N2k", 2000, "Bronze", 3),
        ("N5k", 5000, "Silver", 4),
        ("N10k", 10000, "Silver", 5),
        ("N20k", 20000, "Gold", 6),
        ("N50k", 50000, "Gold", 7),
        ("N100k", 100000, "Platinum", 8),
        ("N250k", 250000, "Platinum", 9),
        ("N500k", 500000, "Diamond", 10),
        ("N1m", 1000000, "Diamond", 11),
        ("N2m", 2000000, "Elite", 12),
        ("N5m", 5000000, "Elite", 13),
        ("N10m", 10000000, "Elite", 14),
        ("N20m", 20000000, "Elite", 15),
        ("N30m", 30000000, "Elite", 16),
        ("N50m", 50000000, "Elite", 17),
    ]

    # Add Packages only if they don't exist
    for name, amount, category, level in packages:
        existing = Package.query.filter_by(name=name).first()
        if not existing:
            db.session.add(Package(name=name, amount=amount, category=category, level=level))
    db.session.commit()

    # Seed default commission rates if not already set
    default_commissions = {
        "Bronze": 0.03,
        "Silver": 0.05,
        "Gold": 0.07,
        "Platinum": 0.10,
        "Diamond": 0.12,
        "Elite": 0.15
    }

    for category, rate in default_commissions.items():
        existing = CommissionConfig.query.filter_by(category=category).first()
        if not existing:
            db.session.add(CommissionConfig(category=category, rate=rate))
    db.session.commit()
