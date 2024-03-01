# {C$50.budget}

<p align="center">
<picture>
    <img src="static/android-chrome-512x512.png" width="256" height="256" alt="https://favicon.io/emoji-favicons/abacus/">
  </picture>
</p>

#### Video Demo:  <https://youtu.be/oGc6LTSLGzg>
#### Description: {C$50.budget} is a web app for personal budgeting created as my Final Project of 2024 CS50x

- Note: Current functionality is limited (vida infra).
- This web application serves as a personal budgeting tool designed to help users manage their finances effectively. It is built using Python with the Flask web framework, along with some JavaScript, HTML, and CSS. The app allows users to track their expenses, set monthly budgets for different categories, and analyze their spending habits. It was inspired by (and uses some code from) Problem Set 9, Finance.

**Features:**
1. **Registration:** New users can register by providing a unique username and password. Passwords are securely hashed before storing in the database.
2. **Dashboard:** Provides an overview of the user's spending, calculating the percentage spent in each category. Upon logging in, users are directed to the dashboard where they can view their budget categories and expenses.
3. **Accounts:** Allows users to add, view, and manage their accounts. Users can specify details such as account name, type, and bank.
4. **Budget:** Displays the user's monthly budget for each category and allows them to modify or add new budget categories.
5. **Transactions:** Enables users to view, add, and delete transactions. Users can import transactions from CSV files exported from supported financial institutions and assign them to specific budget categories.
6. **Authentication:** Implements user authentication features, including registration, login, and password change functionalities.

**Limitations in Current Functionality:**

1. **Limited File Support:** The app currently supports importing transactions from CSV files exported by Chase, Citi, Discover, and one Credit Union. Support for additional file formats or financial institutions may be added in future updates.
2. **Manual Budget Updates:** Budget updates are not automated and require users to manually trigger the update process. Future versions may include automated budget updates based on predefined schedules.
3. **Limited Analytics:** While the app provides basic analytics such as percentage spent in each category, more advanced analytics features such as trend analysis or predictive insights are not included in the current version.

**Future Improvements and Goals:**

1. **Automated Budget Reset:** Implement logic to reset budgets automatically at the beginning of each month.
2. **Advanced Analytics:** Enhance analytics capabilities to provide users with deeper insights into their spending patterns and financial habits.
3. **Enhanced File Support:** Expand file support to include a wider range of formats and financial institutions for transaction importing.
4. **Mobile Optimization:** Optimize the app for mobile devices to provide users with a better experience on smartphones and tablets.
5. **Code Documentation:** Include comments throughout code for better clarity of functions.
6. **Enhanced Customization:** Allow further modifications of accounts, budgets, and transactions.
7. **Optimization:** Refactor code for efficiency. Remove magic numbers and improve code readability.
8. **Automate Imports:** Implement imports of transaction data directly from financial institutions.

This personal budgeting web app offers users a convenient way to manage their finances, track expenses, and stay within budget. While the current version provides essential features for budgeting and expense tracking, future updates aim to enhance functionality and user experience further.


**Further information: Here are details on the implementation of specific functionalities in Flask routes:**
- "/" leads to index.html and displays user's Dashboard.
- "/accounts" leads to accounts.html. Accounts are stored in the SQL database and identified by account_id. This table lists the user specified accounts, account type, bank, initial value (when added), and current value after importing transactions.
- "/budget" lists current budgets and amounts (stored in the SQL database) displayed by budget.html.
- "/update_budgets" sums transactions in each budget and subtracts them from the monthly budget to determine the amount left for spending. Update_budgets is routed after each transaction import, category update, or when transactions are deleted.
- "/categories" lists current budget categories stored in the SQL database and identified by budget_id. This table contains the user specified budgets, keywords (to help identify budget categories upon transaction import), monthly budget, amount spent thus far in each budget, and amount remaining for spending.
- "/update_category" changes the assigned budget category for each transaction via a select menu on the transactions page. After updating the budget category, /update_budgets is called.
- "/transactions" lists imported transactions, stored in the SQL database, along with a description, budget category, and the amount of the transaction.
- "/add_transactions" imports transactions via csv files downloaded from the user's banks' websites. Upon import, it tries to automate budget category selection based on keywords associated with each budget in its SQL table. This works by matching keywords to words from the imported_category or description of the transaction. The import function currently only works with Chase, Citi, Discover, and one Credit Union exported CSV files. Each bank has a different design for the data structure in their csv exports and, at least right now, needs a custom method to import the data correctly.
- "/delete_transactions" deletes all transactions, resets account current values, and budgets. A simple JavaScript function displays a confirmation popup to make sure the user intends to delete all transactions.
