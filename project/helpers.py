import csv
import datetime
import pytz
import requests
import urllib
import uuid

from flask import redirect, render_template, request, session
from functools import wraps
from io import TextIOWrapper


ALLOWED_EXTENSIONS = {'csv'}

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_chase_transactions(requested_file, user_id, account_id, db):
    transaction_import_id = db.execute("SELECT MAX(transaction_import_id) FROM transactions WHERE user_id = ?", user_id)[0]["MAX(transaction_import_id)"]
    if transaction_import_id is None:
        transaction_import_id = 0
    else:
        transaction_import_id += 1
    account_id = request.form.get("account")
    opened_file = TextIOWrapper(requested_file.stream, encoding="utf-8")
    file_data = csv.reader(opened_file)
    next(file_data)
    for row in file_data:
        transaction_date = row[0]
        description = row[2]
        imported_category = row[3]
        type = row[4]
        amount = float(row[5]) if row[5] else 0.0
        memo = row[6]

        db.execute("INSERT INTO transactions (transaction_date, description, imported_category, type, amount, memo, account_id, transaction_import_id, user_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    transaction_date, description, imported_category, type, amount, memo, account_id, transaction_import_id, user_id)

    added_transactions = db.execute(
        """SELECT transactions.transaction_id AS transaction_id, transactions.transaction_date, transactions.description AS description, transactions.imported_category AS import_category, budget_categories.name AS category_name, transactions.type, transactions.amount
        FROM transactions
        JOIN budget_categories ON transactions.user_category_id = budget_categories.budget_id
        WHERE transactions.user_id = ?""", user_id)

    categories = db.execute("SELECT budget_id, name, keywords FROM budget_categories WHERE user_id = ?", user_id)

    for transaction in added_transactions:
        normalized_import_category = transaction["import_category"].strip().lower()  # Normalize import category name
        normalized_description = transaction["description"].strip().lower()  # Normalize import category name
        transaction_keywords = set(normalized_import_category.split() + normalized_description.split())
        user_category_id = 1  # Default value if no match is found
        for keyword in transaction_keywords:
            for category in categories:
                if category.get("keywords"):
                    category_keywords = category.get("keywords").split()
                    for category_keyword in category_keywords:
                        if category_keyword.lower() in keyword:  # Check if keyword matches category name
                            user_category_id = category["budget_id"]
                            break  # Exit loop once a match is found
            if user_category_id != 1:
                break  # Exit loop if a match is found
        db.execute("UPDATE transactions SET user_category_id = ?, account_id = ? WHERE transaction_id = ? AND transaction_import_id = (SELECT MAX(transaction_import_id) FROM transactions)", user_category_id, account_id, transaction["transaction_id"])
    return added_transactions


def process_discover_transactions(requested_file, user_id, account_id, db):
    transaction_import_id = db.execute("SELECT MAX(transaction_import_id) FROM transactions WHERE user_id = ?", user_id)[0]["MAX(transaction_import_id)"]
    if transaction_import_id is None:
        transaction_import_id = 0
    else:
        transaction_import_id += 1
    account_id = request.form.get("account")
    opened_file = TextIOWrapper(requested_file.stream, encoding="utf-8")
    file_data = csv.reader(opened_file)
    next(file_data)
    for row in file_data:
        transaction_date = row[0]
        description = row[2]
        amount = -float(row[3]) if row[3] else 0.0
        imported_category = row[4]

        db.execute("INSERT INTO transactions (transaction_date, description, imported_category, amount, account_id, transaction_import_id, user_id) VALUES(?, ?, ?, ?, ?, ?, ?)",
                    transaction_date, description, imported_category, amount, account_id, transaction_import_id, user_id)

    added_transactions = db.execute(
        """SELECT transactions.transaction_id AS transaction_id, transactions.transaction_date, transactions.description AS description, transactions.imported_category AS import_category, budget_categories.name AS category_name, transactions.type, transactions.amount
        FROM transactions
        JOIN budget_categories ON transactions.user_category_id = budget_categories.budget_id
        WHERE transactions.user_id = ?""", user_id)

    categories = db.execute("SELECT budget_id, name, keywords FROM budget_categories WHERE user_id = ?", user_id)

    for transaction in added_transactions:
        normalized_import_category = transaction["import_category"].strip().lower()  # Normalize import category name
        normalized_description = transaction["description"].strip().lower()  # Normalize import category name
        transaction_keywords = set(normalized_import_category.split() + normalized_description.split())
        user_category_id = 1  # Default value if no match is found
        for keyword in transaction_keywords:
            for category in categories:
                if category.get("keywords"):
                    category_keywords = category.get("keywords").split()
                    for category_keyword in category_keywords:
                        if category_keyword.lower() in keyword:  # Check if keyword matches category name
                            user_category_id = category["budget_id"]
                            break  # Exit loop once a match is found
            if user_category_id != 1:
                break  # Exit loop if a match is found
        db.execute("UPDATE transactions SET user_category_id = ?, account_id = ? WHERE transaction_id = ? AND transaction_import_id = (SELECT MAX(transaction_import_id) FROM transactions)", user_category_id, account_id, transaction["transaction_id"])
    return added_transactions


def process_citi_transactions(requested_file, user_id, account_id, db):
    transaction_import_id = db.execute("SELECT MAX(transaction_import_id) FROM transactions WHERE user_id = ?", user_id)[0]["MAX(transaction_import_id)"]
    if transaction_import_id is None:
        transaction_import_id = 0
    else:
        transaction_import_id += 1
    account_id = request.form.get("account")
    opened_file = TextIOWrapper(requested_file.stream, encoding="utf-8")
    file_data = csv.reader(opened_file)
    next(file_data)
    for row in file_data:
        transaction_date = row[1]
        description = row[2]
        amount = -float(row[3]) if row[3] else -float(row[4])

        db.execute("INSERT INTO transactions (transaction_date, description, amount, account_id, transaction_import_id, user_id) VALUES(?, ?, ?, ?, ?, ?)",
                    transaction_date, description, amount, account_id, transaction_import_id, user_id)

    added_transactions = db.execute(
        """SELECT transactions.transaction_id AS transaction_id, transactions.transaction_date, transactions.description AS description, budget_categories.name AS category_name, transactions.type, transactions.amount
        FROM transactions
        JOIN budget_categories ON transactions.user_category_id = budget_categories.budget_id
        WHERE transactions.user_id = ?""", user_id)

    categories = db.execute("SELECT budget_id, name, keywords FROM budget_categories WHERE user_id = ?", user_id)

    for transaction in added_transactions:
        normalized_description = transaction["description"].strip().lower()  # Normalize import category name
        transaction_keywords = normalized_description.split()
        user_category_id = 1  # Default value if no match is found
        for keyword in transaction_keywords:
            for category in categories:
                if category.get("keywords"):
                    category_keywords = category.get("keywords").split()
                    for category_keyword in category_keywords:
                        if category_keyword.lower() in keyword:  # Check if keyword matches category name
                            user_category_id = category["budget_id"]
                            break  # Exit loop once a match is found
            if user_category_id != 1:
                break  # Exit loop if a match is found
        db.execute("UPDATE transactions SET user_category_id = ?, account_id = ? WHERE transaction_id = ? AND transaction_import_id = (SELECT MAX(transaction_import_id) FROM transactions)", user_category_id, account_id, transaction["transaction_id"])
    return added_transactions


def process_noble_transactions(requested_file, user_id, account_id, db):
    transaction_import_id = db.execute("SELECT MAX(transaction_import_id) FROM transactions WHERE user_id = ?", user_id)[0]["MAX(transaction_import_id)"]
    if transaction_import_id is None:
        transaction_import_id = 0
    else:
        transaction_import_id += 1
    account_id = request.form.get("account")
    opened_file = TextIOWrapper(requested_file.stream, encoding="utf-8")
    file_data = csv.reader(opened_file)
    for _ in range(4):
        next(file_data)
    for row in file_data:
        transaction_date = row[1]
        description = row[3]
        amount = float(row[4]) if row[4] else float(row[5])

        db.execute("INSERT INTO transactions (transaction_date, description, amount, account_id, transaction_import_id, user_id) VALUES(?, ?, ?, ?, ?, ?)",
                    transaction_date, description, amount, account_id, transaction_import_id, user_id)

    added_transactions = db.execute(
        """SELECT transactions.transaction_id AS transaction_id, transactions.transaction_date, transactions.description AS description, budget_categories.name AS category_name, transactions.type, transactions.amount
        FROM transactions
        JOIN budget_categories ON transactions.user_category_id = budget_categories.budget_id
        WHERE transactions.user_id = ?""", user_id)

    categories = db.execute("SELECT budget_id, name, keywords FROM budget_categories WHERE user_id = ?", user_id)

    for transaction in added_transactions:
        normalized_description = transaction["description"].strip().lower()  # Normalize import category name
        transaction_keywords = normalized_description.split()
        user_category_id = 1  # Default value if no match is found
        for keyword in transaction_keywords:
            for category in categories:
                if category.get("keywords"):
                    category_keywords = category.get("keywords").split()
                    for category_keyword in category_keywords:
                        if category_keyword.lower() in keyword:  # Check if keyword matches category name
                            user_category_id = category["budget_id"]
                            break  # Exit loop once a match is found
            if user_category_id != 1:
                break  # Exit loop if a match is found
        db.execute("UPDATE transactions SET user_category_id = ?, account_id = ? WHERE transaction_id = ? AND transaction_import_id = (SELECT MAX(transaction_import_id) FROM transactions)", user_category_id, account_id, transaction["transaction_id"])
    return added_transactions


def update_current_value(db, user_id):
    """Update the current value of each account."""
    account_data = db.execute(
        """SELECT accounts.account_id, accounts.init_value, COALESCE(SUM(transactions.amount), 0) AS sum_transaction_amount
        FROM accounts
        LEFT JOIN transactions ON accounts.account_id = transactions.account_id
        WHERE accounts.user_id = ?
        GROUP BY accounts.account_id""", user_id)

    for account in account_data:
        current_value = account["init_value"] + account["sum_transaction_amount"]
        db.execute("UPDATE accounts SET current_value = ? WHERE account_id = ?", current_value, account["account_id"])

def get_total_cash(db, user_id):
    """Get the total cash value for the user."""
    total_cash = db.execute(
        "SELECT COALESCE(SUM(current_value), 0) as total_cash FROM accounts WHERE type LIKE '%Bank%' AND user_id = ?", user_id
    )[0]["total_cash"]
    return total_cash

def get_total_debt(db, user_id):
    """Get the total debt value for the user."""
    total_debt = db.execute(
        "SELECT COALESCE(SUM(current_value), 0) as total_debt FROM accounts WHERE type LIKE '%Credit Card%' AND user_id = ?", user_id
    )[0]["total_debt"]
    return total_debt

def calculate_net_worth(total_cash, total_debt):
    """Calculate the net worth."""
    net_worth = total_cash + total_debt
    return net_worth

def get_account_data(db, user_id):
    """Get account data for the user."""
    account_data = db.execute(
        """SELECT account_id, name, type, bank, init_value, current_value, user_id
        FROM accounts
        WHERE accounts.user_id = ?
        GROUP BY accounts.account_id""", user_id)
    return account_data
