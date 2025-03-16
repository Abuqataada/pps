from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Package, Referral, Transaction, AccountDetails, WithdrawalRequest, seed_packages
from werkzeug.security import check_password_hash, generate_password_hash
from services.registration_service import register_user, calculate_commission
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
import requests
import json
import os
from flask_migrate import Migrate
from datetime import datetime, timedelta


app = Flask(__name__)
migrate = Migrate(app, db)  # Added for database migrations
# Configure SQLite database
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "for_development")
# Use PostgreSQL from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI", "sqlite:///pps.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Disable debug mode in production
app.config["DEBUG"] = os.getenv("FLASK_ENV", "production") == "development"
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_d7311cf7d33bae105a57562e4b91fc2fd47bbb16")

login_manager = LoginManager(app)
login_manager.login_view = "index"

db.init_app(app=app)

with app.app_context():
        db.create_all()  # Ensure DB is initialized
        seed_packages()  # Run your seed function once the app context is available
        
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/register", methods=["GET", "POST"])
def register():
    global referral_code
    referral_code = request.args.get("referral_code", "")
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        referral_code = request.form.get("referral_code")
        package_id = int(request.form.get("package_id"))

        # Validate required fields
        if not all([name, phone, email, username, password, package_id]):
            flash("All fields are required!", "danger")
            return redirect(url_for("register"))

        # Hash the password
        password_hash = generate_password_hash(password)

        # Call the registration service
        result = register_user(
            name=name,
            phone=phone,
            email=email,
            password_hash=password_hash,
            username=username,
            package_id=package_id,
            referral_code=referral_code
        )

        # Handle registration result
        if "error" in result:
            flash(result["error"], "danger")
        else:
            flash(result["success"], "success")
            return redirect(url_for("login"))

    # Fetch available packages for dynamic package selection
    packages = Package.query.all()
    return render_template("register.html", packages=packages, referral_code=referral_code)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", show_sidebar=False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)  # This handles session automatically
            
            # Get 'next' parameter if it exists
            next_page = request.args.get('next')

            # Redirect based on role
            if next_page:
                return redirect(next_page)
            elif user.is_admin:
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("dashboard"))

        flash("Invalid login credentials", "danger")

    return render_template("login.html", show_sidebar=False)

@app.route("/dashboard")
@login_required
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = current_user
    user_id = current_user.id  # Assuming you're using Flask-Login
    total_referrals = get_total_referrals(user_id)
    # Calculate balance
    user_balance = get_user_balance(user.id)

    return render_template(
        "dashboard.html",
        user=user,
        total_referrals=total_referrals,
        balance=user_balance,
        show_sidebar=True
    )

@app.route('/referral')
@login_required
def referral():
    user_referrals = Referral.query.filter_by(referrer_id=current_user.id).all()
    return render_template('referral.html', referrals=user_referrals, show_sidebar=True)

@app.route('/earnings')
@login_required
def earnings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = current_user
    user_id = current_user.id  # Assuming you're using Flask-Login
    total_referrals = get_total_referrals(user_id)
    referral_link = f"{request.host_url}register?referral_code={user.referral_code}"
    # Calculate balance
    user_balance = get_user_balance(user.id)

    return render_template(
        "earnings.html",
        user=user,
        total_referrals=total_referrals,
        balance=user_balance,
        show_sidebar=True
    )

@app.route('/withdraw-page')
@login_required
def withdraw_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    bank_details = AccountDetails.query.filter_by(user_id=current_user.id).first()
    user = current_user
    # Calculate balance
    user_balance = get_user_balance(user.id)
    
    return render_template('withdraw.html', 
                           bank_details=bank_details, 
                           user=user, 
                           balance=user_balance, 
                           show_sidebar=True)

@app.route('/plans')
def plans():
    # Query all available plans from the database
    plans_list = Package.query.order_by(Package.amount.asc()).all()
    
    return render_template('plans.html', plans=plans_list)




############################################################################################
############################################################################################
#################################### ADMIN SECTION ########################################
############################################################################################
############################################################################################
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("dashboard"))
    
    users = User.query.all()
    
    total_users = len(users)  # Count of total users
    total_referrals = Referral.query.count()  # Count of total referrals

    # Calculate total earnings (assuming User has an 'earnings' field)
    total_earnings = db.session.query(func.sum(User.earnings)).scalar() or 0

    # Fetch recent referrals (assuming Referral has referrer_name, referred_name, package, commission, date)
    recent_referrals = Referral.query.order_by(Referral.created_at.desc()).limit(10).all()
    
    # Calculate total earnings
    total_income = db.session.query(db.func.sum(User.income)).scalar() or 0
    total_commission = db.session.query(db.func.sum(Referral.commission)).scalar() or 0
    
    # Get user growth data for the past 7 days
    today = datetime.today()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    user_growth_dates = [day.strftime('%Y-%m-%d') for day in last_7_days]
    user_growth_counts = [
        db.session.query(func.count(User.id)).filter(func.date(User.created_at) == day.date()).scalar() or 0
        for day in last_7_days
    ]
    
    # Fetch recent deposits (last 5)
    recent_deposits = Transaction.query.filter_by(type="deposit").order_by(Transaction.timestamp.desc()).limit(5).all()

    # Fetch recent withdrawals (last 5)
    recent_withdrawals = Transaction.query.filter_by(type="withdrawal").order_by(Transaction.timestamp.desc()).limit(5).all()

    return render_template(
        "admin/admin_dashboard.html",
        users=users,
        total_users=total_users,
        total_referrals=total_referrals,
        total_earnings=total_earnings,
        recent_referrals=recent_referrals,
        total_income=total_income,
        total_commission=total_commission,
        user_growth_dates=user_growth_dates,
        user_growth_counts=user_growth_counts,
        recent_deposits=recent_deposits,
        recent_withdrawals=recent_withdrawals,
        show_sidebar=True
    )

@app.route('/admin/withdrawals')
@login_required
def admin_withdrawals():
    if not current_user.is_admin:
        return redirect(url_for('login'))

    pending_requests = WithdrawalRequest.query.filter_by(status="pending").all()
    return render_template("admin/withdrawals.html", pending_requests=pending_requests)

@app.route('/admin/withdrawal/<int:request_id>/update', methods=['POST'])
@login_required
def update_withdrawal(request_id):
    if not current_user.is_admin:
        flash("Error: Unautorized access", "danger")
        return redirect(url_for(dashboard))

    withdrawal_request = WithdrawalRequest.query.get(request_id)
    if not withdrawal_request:
        flash("Withdrawal request not found!", "danger")
        return redirect(url_for(admin_dashboard))

    action = request.form.get('action')  # 'approve' or 'reject'

    if action == 'approve':
        withdrawal_request.status = 'approved'

        # Log the withdrawal transaction
        transaction = Transaction(user_id=withdrawal_request.user_id, amount=withdrawal_request.amount, type="withdrawal")
        db.session.add(transaction)
        flash("Withdrawal request approved successfully!", "success")

    elif action == 'reject':
        withdrawal_request.status = 'rejected'
        flash("Withdrawal request rejected successfully!", "success")

        # Refund the amount to the user
        #withdrawal_request.user.balance += withdrawal_request.amount

    db.session.commit()
    
    return redirect(url_for(admin_dashboard))



































##############################################################################
#################################### TRANSACTIONS ############################
##############################################################################

@app.route('/start_payment', methods=['POST'])
def start_payment():
    # Get the amount from the form data
    amount = request.form.get('amount')
    if not amount or not amount.isdigit():
        return "Invalid amount entered", 400
    
    if float(amount) < float(current_user.package.amount):
        flash("Amount is less than the package price", "danger")
        return redirect(url_for('deposit', amount=current_user.package.amount))

    # Convert the amount to kobo (Paystack expects amounts in kobo)
    amount_kobo = int(amount) * 100
    
    url = "https://api.paystack.co/transaction/initialize"
    data = {
        "email": current_user.email,  # customer's email
        "amount": amount_kobo,
        "callback_url": f"{request.host_url}payment-success",  # callback URL
        "metadata": {"cancel_action": f"{request.host_url}deposit"}
    }
    
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Make the POST request to Paystack API
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        result = response.json()
        # Redirect to the Paystack payment page
        authorization_url = result['data']['authorization_url']
        return redirect(authorization_url)
    else:
        return "Failed to initialize payment. Please try again later.", 500


@app.route('/payment-success', methods=['GET'])
def payment_success():
    reference = request.args.get('reference')
    
    if not reference:
        flash("No reference provided", "danger")
        return redirect(url_for('deposit'))

    # Verify the transaction with Paystack
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    result = response.json()

    if result.get("status") and result["data"]["status"] == "success":
        amount = result["data"]["amount"] / 100  # Convert from kobo to Naira
        email = result["data"]["customer"]["email"]

        try:
            # Fetch the user who made the payment
            user = User.query.filter_by(email=email).first()
            if not user:
                flash("User not found!", "danger")
                return redirect(url_for('deposit'))

            # Fetch the referrer (if any)
            referrer = User.query.get(user.referrer_id)

            # Update user's balance
            user.deposit += amount

            # Log the deposit
            deposit_log = Transaction(user_id=user.id, amount=amount, type="deposit")
            db.session.add(user)
            db.session.add(deposit_log)

            # Only calculate commission if there is a valid referrer
            if referrer:
                commission = calculate_commission(referrer, user)

                # Find the referral entry and update status & commission
                referral_entry = Referral.query.filter_by(referred_id=user.id, referrer_id=referrer.id).first()
                if referral_entry:
                    referral_entry.status = "paid"
                    referral_entry.commission = (referral_entry.commission or 0) + commission
                    db.session.add(referral_entry)

                # Update referrer's earnings
                referrer.earnings = (referrer.earnings or 0) + commission
                db.session.add(referrer)

            # Commit all changes
            db.session.commit()

            return redirect(url_for('deposit_success', amount=amount))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Database Error: {e}", "danger")
            return redirect(url_for('deposit', amount=amount))

        except Exception as e:
            db.session.rollback()
            flash(f"Unexpected Error: {e}", "danger")
            return redirect(url_for('deposit', amount=amount))

    else:
        flash("Error: Transaction verification failed.", "danger")
        return redirect(url_for('deposit', amount=amount))

@app.route('/deposit-success')
def deposit_success():
    amount = request.args.get('amount')

    # Ensure amount is valid before converting to int
    if not amount or not amount.isdigit():
        flash("Your deposit is successful!", "success")
        return redirect(url_for('dashboard'))  # Redirect to a safe page

    amount = int(amount)

    return f"""
    <h1>Payment Successful</h1>
    <p>You have deposited NGN {amount} successfully.</p>
    <a href="{url_for('deposit', amount=amount)}">Return to PPS</a>
    """

@app.route("/deposit/<int:amount>", methods=["GET", "POST"])
@login_required
def deposit(amount):
    user = current_user
    total_referrals = get_total_referrals(user.id)
    user_balance = get_user_balance(user.id)

    return render_template(
        "deposit.html",
        user=user,
        balance=user_balance,
        amount=amount,
        show_sidebar=True
    )

###################################################################
###################################################################
########################### WITHDRAWAL ############################
###################################################################
###################################################################
## Withdrawals
@app.route('/withdraw', methods=['POST'])
def withdraw():
    bank_details = AccountDetails.query.filter_by(user_id=current_user.id).first()

    if not bank_details:
        flash("Bank details are required for the withdrawal destination!", "danger")
        return redirect(url_for('withdraw_page'))

    # Get form data
    amount = request.form.get('amount')
    account_name = bank_details.account_name
    account_number = bank_details.account_number
    bank_name = bank_details.bank_name

    if not amount:
        flash("Amount is required to initiate withdrawal!", "danger")
        return redirect(url_for('withdraw_page')), 400

    # Check if user has enough balance
    if current_user.total_withdrawable < float(amount):
        flash("Insufficient balance!", "danger")
        return redirect(url_for('withdraw_page')), 400

    # Deduct balance before making the payout
    current_user.total_withdrawable -= float(amount)
    db.session.commit()

    # Process withdrawal (Paystack Transfer API example)
    url = "https://api.paystack.co/transfer"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "source": "balance",
        "amount": int(amount) * 100,  # Convert to kobo
        "recipient": {
            "type": "nuban",
            "name": bank_name,
            "account_number": account_number,
            "bank_code": "058"  # Replace with the actual bank code
        },
        "reason": "Withdrawal request"
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    if result["status"]:
        # Update withdrawal history or notify user
        return redirect(url_for('withdrawal_success', amount=amount))
    else:
        # Rollback balance in case of failure
        current_user.deposit += float(amount)
        db.session.commit()
        flash("Withdrawal failed", "danger")
        return redirect(url_for('withdraw_page'))

@app.route('/withdrawal-success')
def withdrawal_success():
    amount = request.args.get('amount')
    return f"""
    <h1>Withdrawal Successful</h1>
    <p>Your withdrawal of NGN {amount} is being processed.</p>
    <a href=f"{request.host_url}withdraw">Return to MPS</a>
    """

@app.route('/request-withdraw', methods=['POST'])
@login_required
def request_withdrawal():
    bank_details = AccountDetails.query.filter_by(user_id=current_user.id).first()

    if not bank_details:
        flash("Bank details are required for the withdrawal destination!", "danger")
        return redirect(url_for('withdraw_page'))
    
    amount = request.form.get('amount', type=float)

    if not amount or amount <= 0:
        flash("Error: Invalid amount", "danger")
        return redirect(url_for('withdraw_page'))

    if current_user.total_withdrawable < amount:
        flash("Error: Insufficient balance", "danger")
        return redirect(url_for('withdraw_page'))

    # Create withdrawal request
    withdrawal_request = WithdrawalRequest(user_id=current_user.id, amount=amount)
    db.session.add(withdrawal_request)

    # Deduct from user's balance (assuming balance should be locked until approval)
    if current_user.earnings < amount:
        balance = amount - current_user.earnings
        current_user.deposit = current_user.deposit - balance
        
    if current_user.earnings > amount:
        balance = current_user.earnings - amount
        current_user.deposit = current_user.deposit - balance
    db.session.commit()

    flash("Withdrawal request submitted successfully!", "success")
    return redirect(url_for('withdraw_page'))

def update_balances(amount):
    income = current_user.income
    commission = current_user.commission
    deposit = current_user.deposit
    earnings = current_user.earnings
    
    #subtract from commission, income and deposit in order
    commission = max(0, commission - amount)
    amount = max(0, amount - commission)
    income = max(0, income - amount)
    amount = max(0, amount - income)
    deposit = max(0, deposit - amount)
    
    # Update earnings and total_withdrawable
    current_user.earnings = income + commission
    current_user.total_withdrawable = earnings + deposit
    
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))






















#######################
#######################
# Number of referrals
#######################
#######################
def get_total_referrals(user_id):
    # Count how many referrals this user made
    total_referrals = Referral.query.filter_by(referrer_id=user_id).count()
    return total_referrals

#######################
#######################
# Getting Balance
#######################
#######################
def get_user_balance(user_id):
    # Calculate deposits
    deposits = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=user_id, type='deposit').scalar() or 0
    
    # Calculate withdrawals
    withdrawals = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=user_id, type='withdrawal').scalar() or 0
    
    # Calculate balance
    balance = deposits - withdrawals
    return balance

##############################################################################
#################################### UTILITIES ###############################
##############################################################################

@app.route('/check-bank-details', methods=['GET'])
def check_bank_details():
    # Get the current user's bank details
    bank_details = AccountDetails.query.filter_by(user_id=current_user.id).first()
    
    if bank_details:
        # Return both the status and the bank details
        return jsonify({
            "has_bank_details": True,
            "bank_details": {
                "bank_name": bank_details.bank_name,
                "account_number": bank_details.account_number,
                "account_name": bank_details.account_name
            }
        })
    else:
        # Return just the status if no bank details are found
        return jsonify({"has_bank_details": False})

@app.route('/save-bank-details', methods=['POST'])
def save_bank_details():
    bank_name = request.form.get('bank_name')
    account_number = request.form.get('account_number')
    account_name = request.form.get('account_name')

    # Validation
    if not bank_name or len(bank_name) < 2:
        flash("Bank name must be at least 2 characters long.", "danger")
        return redirect(url_for('withdraw_page'))

    if not account_number or not account_number.isdigit() or len(account_number) != 10:
        flash("Account number must be 10 digits.", "danger")
        return redirect(url_for('withdraw_page'))

    if not account_name or len(account_name) < 2:
        flash("Account name must be at least 2 characters long.", "danger")
        return redirect(url_for('withdraw_page'))

    # Check if user already has bank details
    existing_bank_detail = AccountDetails.query.filter_by(user_id=current_user.id).first()

    if existing_bank_detail:
        flash("Bank details already exist. Please edit instead.", "danger")
        return redirect(url_for('withdraw_page'))

    # Save to database
    new_bank_detail = AccountDetails(
        user_id=current_user.id,
        bank_name=bank_name,
        account_number=account_number,
        account_name=account_name
    )

    db.session.add(new_bank_detail)
    db.session.commit()

    flash("Bank details saved successfully.", "success")
    return redirect(url_for('withdraw_page'))  # Replace with the appropriate route


@app.route('/update-bank-details', methods=['POST'])
def update_bank_details():
    #data = request.get_json()
    bank_name = request.form['bank_name']
    account_number = request.form['account_number']
    account_name = request.form['account_name']

    # Update the database with the new bank details
    bank_details = AccountDetails.query.filter_by(user_id=current_user.id).first()
    if bank_details:
        bank_details.bank_name = bank_name
        bank_details.account_number = account_number
        bank_details.account_name = account_name
        db.session.commit()
        flash("Bank details updated successfully!", "success")
        return redirect(url_for('withdraw_page')), 200
    else:
        flash("Bank details not found!", "danger")
        return redirect(url_for('withdraw_page')), 404


@app.route('/remove-bank-details', methods=['POST'])
@login_required
def remove_bank_details():
    try:
        # Fetch the user's bank details from the database
        bank_details = AccountDetails.query.filter_by(user_id=current_user.id).first()
        if not bank_details:
            flash("No bank details found for this user", "danger")
            return redirect(url_for('withdraw_page'))

        # Remove the bank details
        db.session.delete(bank_details)
        db.session.commit()

        flash("Bank details removed successfully!", "success")
        return redirect(url_for('withdraw_page'))
    except Exception as e:
        flash(f"Error removing bank details: {e}", "danger")
        return redirect(url_for('withdraw_page')), 404





















if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_packages()
    app.run(host="0.0.0.0", port=5000, debug=True)
