from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Package, Referral, Transaction, AccountDetails, seed_packages
from werkzeug.security import check_password_hash, generate_password_hash
from services.registration_service import register_user, calculate_commission
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
import requests
import json
import os


app = Flask(__name__)
# Configure SQLite database
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "for_development")
# Use PostgreSQL from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///pps.db")
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pps.db'  # Change to PostgreSQL if needed
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Disable debug mode in production
app.config["DEBUG"] = os.getenv("FLASK_ENV", "production") == "development"
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_d7311cf7d33bae105a57562e4b91fc2fd47bbb16")

login_manager = LoginManager(app)
login_manager.login_view = "login"

db.init_app(app=app)

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
        print("New user reistered!")

        # Handle registration result
        if "error" in result:
            flash(result["error"], "danger")
            print("Error caught", result["error"])
        else:
            flash(result["success"], "success")
            print("Success achieved")
            return redirect(url_for("login"))

    # Fetch available packages for dynamic package selection
    packages = Package.query.all()
    return render_template("register.html", packages=packages, referral_code=referral_code)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        else:
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
    print(referral_link)
    # Calculate balance
    user_balance = get_user_balance(user.id)

    return render_template(
        "earnings.html",
        user=user,
        total_referrals=total_referrals,
        balance=user_balance,
        show_sidebar=True
    )








































##############################################################################
#################################### TRANSACTIONS ############################
##############################################################################

@app.route('/start_payment', methods=['POST'])
def start_payment():
    # Get the amount from the form data
    amount = request.form.get('amount')
    if not amount or not amount.isdigit():
        return "Invalid amount entered", 400

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
    print(reference)
    
    if not reference:
        return jsonify({"error": "No reference provided"}), 400

    # Verify the transaction with Paystack
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    result = response.json()
    print(result)

    if result.get("status") and result["data"]["status"] == "success":
        amount = result["data"]["amount"] / 100  # Convert from kobo to Naira
        email = result["data"]["customer"]["email"]

        try:
            # Fetch the user who made the payment
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Fetch the referrer
            referrer = User.query.get(user.referrer_id)

            # Update user's balance
            user.deposit += amount

            # Initialize referral_entry to avoid referencing an undefined variable
            referral_entry = None

            # If the user was referred, update referral details
            if referrer:
                # Calculate commission
                commission = calculate_commission(referrer, user)
                
                # Find the referral entry and update status & commission
                referral_entry = Referral.query.filter_by(referred_id=user.id, referrer_id=referrer.id).first()
                if referral_entry:
                    referral_entry.status = "paid"
                    referral_entry.commission += commission

                earnings = referrer.income + referral_entry.commission
                referrer.earnings += earnings
            # Log the transaction
            deposit_log = Transaction(user_id=user.id, amount=amount, type="deposit")

            # Add objects to session, only if they are not None
            db.session.add(user)
            db.session.add(deposit_log)
            if referrer:
                db.session.add(referrer)
            if referral_entry:
                db.session.add(referral_entry)

            # Commit all changes
            db.session.commit()

            return redirect(url_for('deposit_success', amount=amount))

        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Database Error: {e}")
            return jsonify({"error": "Transaction failed", "details": str(e)}), 500

        except Exception as e:
            db.session.rollback()
            print(f"Unexpected Error: {e}")
            return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

    else:
        return jsonify({"error": "Transaction verification failed"}), 400

@app.route('/deposit-success')
def deposit_success():
    amount = request.args.get('amount')
    return f"""
    <h1>Payment Successful</h1>
    <p>You have deposited NGN {amount} successfully.</p>
    <a href="{request.host_url}deposit">Return to PPS</a>
    """

@app.route("/deposit")
@login_required
def deposit():
    user = current_user
    user_id = current_user.id  # Assuming you're using Flask-Login
    total_referrals = get_total_referrals(user_id)
    # Calculate balance
    user_balance = get_user_balance(user.id)

    return render_template(
        "deposit.html",
        user=user,
        balance=user_balance,
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
        return jsonify({"error": result.get("message", "Withdrawal failed")}), 400

@app.route('/withdrawal-success')
def withdrawal_success():
    amount = request.args.get('amount')
    return f"""
    <h1>Withdrawal Successful</h1>
    <p>Your withdrawal of NGN {amount} is being processed.</p>
    <a href=f"{request.host_url}withdraw">Return to MPS</a>
    """

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))






















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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_packages()
    app.run(host="0.0.0.0", port=5000)
