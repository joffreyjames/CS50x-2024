import os
import datetime
import csv

from cs50 import SQL
from decimal import Decimal
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from io import TextIOWrapper
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from helpers import apology, login_required, usd, allowed_file, process_chase_transactions, process_discover_transactions, process_citi_transactions, process_noble_transactions

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///budget.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show dashboard"""
    user_id = session["user_id"]

    index_data = db.execute(
        "SELECT name, monthly_budget, budget_spent, remaining_budget FROM budget_categories WHERE user_id = ? AND name != 'Uncategorized'", user_id
    )
    #total_budget_spent = db.execute("SELECT SUM(budget_spent) AS total_budget_spent WHERE user_id = ?", user_id)

    total_budget_spent = Decimal(0)
    for category in index_data:
        total_budget_spent += Decimal(category["budget_spent"])

    # Calculate the percentage spent in each category
    for category in index_data:
        category["percentage_spent"] = (Decimal(category["budget_spent"]) / total_budget_spent) * 100

    total_monthly_budget = db.execute(
        "SELECT SUM(monthly_budget) as total_monthly_budget FROM budget_categories WHERE user_id = ? AND name != 'Uncategorized'", user_id
    )[0]["total_monthly_budget"]
    total_remaining_budget = db.execute(
        "SELECT SUM(remaining_budget) as total_remaining_budget FROM budget_categories WHERE user_id = ? AND name != 'Uncategorized'", user_id
    )[0]["total_remaining_budget"]

    if request.method == "GET":
        return render_template("index.html", index_data=index_data, total_monthly_budget=total_monthly_budget, total_remaining_budget=total_remaining_budget, usd=usd)


@app.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts():
    """Show list of accounts"""

    user_id = session["user_id"]

    if request.method == "GET":
        account_data = db.execute(
        """SELECT accounts.account_id, accounts.name, accounts.type, accounts.bank, accounts.init_value, accounts.current_value, accounts.user_id, SUM(transactions.amount) AS sum_transaction_amount
        FROM accounts
        JOIN transactions ON accounts.account_id = transactions.account_id
        WHERE accounts.user_id = ?
        GROUP BY accounts.account_id""", user_id)
        for account in account_data:
            current_value = account["init_value"] + account["sum_transaction_amount"]
            db.execute("UPDATE accounts SET current_value = ? WHERE account_id = ?", current_value, account["account_id"])

        total_cash = db.execute(
            "SELECT SUM(current_value) as total_cash FROM accounts WHERE type LIKE '%Bank%' AND user_id = ?", user_id
        )[0]["total_cash"]
        total_debt = db.execute(
            "SELECT SUM(current_value) as total_debt FROM accounts WHERE type LIKE '%Credit Card%' AND user_id = ?", user_id
        )[0]["total_debt"]
        net_worth = total_cash + total_debt

        account_data_get = db.execute(
        """SELECT accounts.account_id, accounts.name, accounts.type, accounts.bank, accounts.init_value, accounts.current_value, accounts.user_id, SUM(transactions.amount) AS sum_transaction_amount
        FROM accounts
        JOIN transactions ON accounts.account_id = transactions.account_id
        WHERE accounts.user_id = ?
        GROUP BY accounts.account_id""", user_id)
        return render_template("accounts.html", account_data=account_data_get, total_cash=total_cash, total_debt=total_debt, net_worth=net_worth, usd=usd)

    else:
        account_name = request.form.get("name")
        account_type = request.form.get("type")
        account_bank = request.form.get("bank")
        account_init_value = 0
        account_current_value = 0
        if not account_name:
            return apology("Please enter name of account.")
        elif not account_type:
            return apology("Please enter type of account.")
        elif not account_bank:
            return apology("Please enter the bank where the account is located.")
        else:
            db.execute("INSERT INTO accounts(name, type, bank, init_value, current_value, user_id) VALUES(?, ?, ?, ?, ?, ?)",
                   account_name, account_type, account_bank, account_init_value, account_current_value, user_id)

            flash(f"Account {account_name}, a {account_type} from {account_bank} was added!")
            return redirect("/accounts")


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    """Show monthly budget"""

    user_id = session["user_id"]
    categories = db.execute(
        "SELECT name, monthly_budget, budget_spent, remaining_budget FROM budget_categories WHERE user_id = ?", user_id
    )
    total_monthly_budget = db.execute(
        "SELECT SUM(monthly_budget) as total_monthly_budget FROM budget_categories WHERE user_id = ?", user_id
    )[0]["total_monthly_budget"]
    total_remaining_budget = db.execute(
        "SELECT SUM(remaining_budget) as total_remaining_budget FROM budget_categories WHERE user_id = ?", user_id
    )[0]["total_remaining_budget"]
    if request.method == "GET":
        return render_template("budget.html", categories=categories, total_monthly_budget=total_monthly_budget, total_remaining_budget=total_remaining_budget, usd=usd)

@app.route("/update_budgets", methods=["GET", "POST"])
@login_required
def update_budgets():
    """Show monthly budget"""

    user_id = session["user_id"]

    db.execute("""
        UPDATE budget_categories
        SET budget_spent = (
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE transactions.user_category_id = budget_categories.budget_id
        )
        WHERE budget_categories.user_id = ?""", user_id)

    db.execute("""
        UPDATE budget_categories
        SET remaining_budget = monthly_budget - budget_spent
        WHERE budget_categories.user_id = ?""", user_id)

    return redirect("/transactions")


@app.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    """Modify budget categories"""

    user_id = session["user_id"]
    categories = db.execute(
        "SELECT name, monthly_budget FROM budget_categories WHERE user_id = ?", user_id
    )
    total_monthly_budget = db.execute(
        "SELECT SUM(monthly_budget) as total_monthly_budget FROM budget_categories WHERE user_id = ?", user_id
    )[0]["total_monthly_budget"]
    if request.method == "GET":
        return render_template("categories.html", categories=categories, total_monthly_budget=total_monthly_budget, usd=usd)
    else:
        budget_name = request.form.get("name")
        monthly_budget = request.form.get("monthly_budget")
        if not budget_name:
            return apology("Please enter a category.")
        elif not monthly_budget:
            monthly_budget = 0

        db.execute("INSERT INTO budget_categories(name, monthly_budget, user_id) VALUES(?, ?, ?)",
                   budget_name, monthly_budget, user_id)
        flash(f"Monthly {budget_name} budget of {monthly_budget} was added!")
        return redirect("/budget")


@app.route("/update_category", methods=["GET", "POST"])
@login_required
def update_category():
    """Update categories for transactions"""
    user_id = session["user_id"]

    # Iterate over form data to update categories for transactions
    for transaction_id, category_id in request.form.items():
        # Extract transaction ID from form data
        if transaction_id.startswith("category_"):
            transaction_id = transaction_id.split("_")[1]

            # Update the category for the transaction in the database
            db.execute("UPDATE transactions SET user_category_id = ? WHERE transaction_id = ? AND user_id = ?", category_id, transaction_id, user_id)

    flash(f"Budget category updated successfully!")
    return redirect("/update_budgets")

@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    """Show list of transactions"""

    user_id = session["user_id"]
    transactions = db.execute(
        """SELECT transactions.transaction_id, transactions.transaction_date, transactions.description, transactions.imported_category, transactions.user_category_id, budget_categories.name AS category_name, transactions.type, transactions.amount
        FROM transactions
        JOIN budget_categories ON transactions.user_category_id = budget_categories.budget_id
        WHERE transactions.user_id = ?""", user_id)
    categories = db.execute("SELECT name AS category_name, budget_id FROM budget_categories")

    if request.method == "GET":
        return render_template("transactions.html", transactions=transactions, categories=categories, usd=usd)
    elif request.form.get("add_transactions"):
        return redirect("/add_transactions")
    elif request.form.get("delete_transactions"):
        return redirect("/delete_transactions")
    else:
        return redirect("/update_category")


@app.route("/add_transactions", methods=["GET", "POST"])
@login_required
def add_transactions():
    """Add to list of transactions"""

    user_id = session["user_id"]
    if request.method == "GET":
        accounts = db.execute("SELECT account_id, name FROM accounts WHERE user_id = ?", user_id)
        return render_template("add_transactions.html", accounts=accounts)
    else:
        if "csv_file" not in request.files:
            return apology("Please select a file.")
        requested_file = request.files["csv_file"]
        if requested_file.filename == "":
            return apology("No selected file.")
        # Currently works with Chase, Citi, Discover, and one Credit Union
        if requested_file and allowed_file(requested_file.filename):
            account_id = request.form.get("account")  # Get the selected account_id from the form
            if "chase" in requested_file.filename.lower():
                process_chase_transactions(requested_file, user_id, account_id, db)
                flash(f"Transactions successfully uploaded from Chase export: {requested_file.filename}!")
                return redirect("/update_budgets")
            elif "discover" in requested_file.filename.lower():
                process_discover_transactions(requested_file, user_id, account_id, db)
                flash(f"Transactions successfully uploaded from Discover export: {requested_file.filename}!")
                return redirect("/update_budgets")
            elif "since" in requested_file.filename.lower():
                process_citi_transactions(requested_file, user_id, account_id, db)
                flash(f"Transactions successfully uploaded from Citi export: {requested_file.filename}!")
                return redirect("/update_budgets")
            elif "export" in requested_file.filename.lower():
                process_noble_transactions(requested_file, user_id, account_id, db)
                flash(f"Transactions successfully uploaded from NobleCU export: {requested_file.filename}!")
                return redirect("/update_budgets")


@app.route("/delete_transactions", methods=["GET", "POST"])
@login_required
def delete_transactions():
    """Delete all transactions and reset account current_values"""

    user_id = session["user_id"]
    if request.method == "POST":
        db.execute("DELETE FROM transactions WHERE user_id = ?", user_id)
        #db.execute("UPDATE accounts SET current_value = 0 WHERE account_id = 6")
        #db.execute("UPDATE accounts SET current_value = 0 WHERE account_id = 8")
        #db.execute("UPDATE accounts SET current_value = 0 WHERE account_id = 9")
        #db.execute("UPDATE accounts SET current_value = 0 WHERE account_id = 10")
        flash(f"Transactions deleted! Accounts and budgets reset!")
        return redirect("/update_budgets")


# To Do

#def reset_budgets():
    # Logic to reset budgets goes here
    # For example, update budget amounts in the database

# Store previous month's budgets
#def store_previous_month_budgets():
    #current_month = datetime.now().month
    #previous_month = current_month - 1 if current_month > 1 else 12

    # Logic to archive previous month's budgets
    # For example, insert budget data into a historical table

# Trigger budget reset and storage process
#if datetime.now().day == 1:
    #reset_budgets()
    #store_previous_month_budgets()













@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username.", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password.", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("Invalid username and/or password.", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirmation")

    if not username:
        return apology("Must provide username.")
    elif not password:
        return apology("Must provide password.")
    elif not confirm_password:
        return apology("Please confirm password.")
    elif password != confirm_password:
        return apology("Passwords must match.")

    hashed_password = generate_password_hash(password)

    try:
        db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", username, hashed_password)
    except:
        return apology("Username already registered.")

    flash(f"Registration of {username} successful!")
    return redirect("/")


@app.route("/changepassword", methods=["GET", "POST"])
def change_password():
    """Change user password"""

    user_id = session["user_id"]

    if request.method == "GET":
        return render_template("changepw.html")

    current_pw = request.form.get("current_password")
    new_pw = request.form.get("new_password")
    confirm_new_pw = request.form.get("confirm_new_password")

    if not current_pw:
        return apology("Please input current password.")
    elif not new_pw:
        return apology("Please input new password.")
    elif not confirm_new_pw:
        return apology("Please enter new password twice.")
    elif new_pw != confirm_new_pw:
        return apology("Passwords must match.")

    old_password = db.execute("SELECT hash FROM users WHERE id = ?", user_id)
    if len(old_password) != 1 or not check_password_hash(old_password[0]["hash"], current_pw):
        return apology("Incorrect password")

    hash_new_pw = generate_password_hash(new_pw)
    db.execute("UPDATE users SET hash = ? WHERE id = ?", hash_new_pw, user_id)

    return redirect("/logout")
