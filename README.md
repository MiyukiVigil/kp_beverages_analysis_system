# Kopitiam Point of Sale & Analytics System

A Streamlit-based Point of Sale (POS) and daily reconciliation application designed specifically for a Kopitiam. It tracks daily transactions, manages menu pricing, reconciles physical coffee ground inventory against system expectations, and provides a comprehensive business analytics dashboard.

## Project Architecture

The application has been refactored into a modular structure to separate the user interface routing, business logic, and data processing.

* **app.py**: The main entry point. It initializes the application, applies global CSS styling, and handles sidebar navigation to route users to the appropriate modules.
* **config.py**: Stores global constants, default settings, and file path definitions.
* **utils.py**: Contains all helper functions for file Input/Output, data cleaning, pricing lookups, and historical data aggregation.
* **pos_view.py**: Houses the UI and logic for the POS Terminal, transaction ledger editing, and the daily end-of-day reconciliation reports.
* **analytics_view.py**: Contains the UI and logic for the Business Analytics Dashboard, including temporal filtering, trend charts, item velocity, and data extraction.
* **menu_view.py**: The Database Maintenance module for adding, updating, or removing menu items and variants.
* **exporter.py**: A utility module dedicated to formatting and generating downloadable PDF documents and multi-sheet Excel workbooks.

## Core Features

### 1. POS Terminal & Ledger
* **Transaction Logging**: Rapidly append new sales to the daily ledger with modifiers like Takeaway, Kosong (no sugar), and Digital Payment (QR).
* **Dynamic Editing**: Review and modify the day's ledger directly within an editable data grid.
* **Real-time Totals**: View gross revenue, expected cash drawer balances, and digital collection totals.

### 2. Inventory Reconciliation
* **Recipe Configuration**: Define expected coffee ground usage weights for hot and cold beverages.
* **Physical vs. System Tracking**: Input the actual physical weight of coffee grounds used at the end of the day. The system calculates the variance against the expected usage based on the day's sales volume, flagging significant discrepancies.

### 3. Business Analytics Dashboard
* **Custom Filtering**: Analyze sales data across specific date ranges.
* **Financial Trends**: Aggregate revenue temporally by day, week, or month.
* **Item Velocity**: Identify top-selling items and segment output by variant architecture (e.g., Hot vs. Cold volume).
* **Period-over-Period Analysis**: Contrast revenue, digital payment distribution, and output volume between two independent timeframes (e.g., this week vs. last week).

### 4. Database Maintenance
* Manage the beverage catalog through an interactive grid.
* Configure unique prices for different variants (e.g., Hot vs. Cold).

## Local Data Storage

The system operates without a traditional SQL database, relying on local JSON file storage for easy backup and portability.
* **menu.json**: Stores the active menu catalog and pricing.
* **settings.json**: Stores inventory recipe configurations.
* **sales/**: A directory containing daily transaction logs, formatted as `YYYY-MM-DD.json`.

## Installation & Setup

1.  **Prerequisites**: Ensure you have Python 3.8 or higher installed.
2.  **Install Dependencies**: Install the required Python packages. At a minimum, the system requires Streamlit and Pandas. (Depending on your `exporter.py` setup, you may also need libraries like `openpyxl` for Excel and `fpdf2` for PDFs).
    ```bash
    pip install streamlit pandas openpyxl fpdf2
    ```
3.  **Run the Application**: Navigate to the project directory in your terminal and execute the Streamlit run command.
    ```bash
    streamlit run app.py
    ```

## Usage Workflow

1.  **Start of Day**: Open the POS Terminal module. Verify the Working Date in the sidebar.
2.  **During Operations**: Use the Transaction Entry tab to log customer orders.
3.  **End of Day**: Navigate to the Daily Reconciliation tab. Weigh the physical coffee grounds used throughout the day and input this value. Review the calculated variance and finalize the ledger.
4.  **Reporting**: Download the Daily End of Day Report (PDF or Excel) for your records.