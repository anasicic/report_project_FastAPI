# report_project_FastAPI

**report_project_FastAPI** is a web application based on the MVC (Model-View-Controller) architecture, developed in FastAPI. The application allows for the input of invoices and reporting on total expenses by cost centers.

## Contents

- [Running the Server](#running-the-server)
- [Application Structure](#application-structure)
- [Database Setup](#database-setup)
- [Features](#features)
- [Technologies](#technologies)

---

## Running the Server

To run the project locally, follow these steps:

1. **Clone the Repository**:

    If you are downloading the project from GitHub, clone the repository using `git clone`:

    ```bash
    git clone https://github.com/anasicic/report_project_FastAPI.git
    ```

2. **Navigate to the Project Directory**:

    After cloning the project, navigate to the project directory:

    ```bash
    cd app
    ```

3. **Create a Virtual Environment**:

    It is recommended to use a virtual environment for package installation:

    ```bash
    python -m venv venv
    ```

4. **Activate the Virtual Environment**:

    On Windows systems:

    ```bash
    venv\Scripts\activate
    ```

    On Linux or macOS systems:

    ```bash
    source venv/bin/activate
    ```

5. **Install Required Packages**:

    ```bash
    pip install -r requirements.txt
    ```

6. **Run the Development Server**:

    ```bash
    uvicorn main:app --reload
    ```

7. **Open a Browser and Go To**:

    ```url
    http://127.0.0.1:8000/
    ```

---

## Application Structure

The application consists of several modules within the `app` directory, including:

- **auth.py**: This module handles user authentication. It includes functionalities for login, registration, and logout of users. It also provides route protection to ensure that only logged-in users can access certain parts of the application.

- **admin.py**: A module for administrative functions. Here you will find endpoints that allow administrators to add, delete, or edit users, suppliers, types of expenses, cost centers, and generate reports on total expenses by cost center.

- **invoices.py**: This module manages all functions related to invoices. It includes capabilities for inputting, updating, deleting, and viewing invoices.

- **users.py**: A module that manages user data. It contains functionalities for retrieving information about users, updating their profiles, and managing user accounts.

---


## Database Setup

FastAPI uses SQLAlchemy to manage the database. To set up the database, follow these steps:

1. **Install Required Packages**:

   If you haven't already, add SQLAlchemy and SQLite to your requirements:

   ```bash
   pip install sqlalchemy databases[sqlite]

---


## Features

- **User Authentication**: Login, registration, and logout.
- **Administrative Functions**: Adding and deleting users, suppliers, types of expenses, cost centers, and generating reports.
- **Invoice Management**: Adding, updating, and deleting invoices.
- **Data Visualization**: Expense reports with graphical representations and export options to Excel.

---

## Technologies

- **FastAPI** - Web framework for backend
- **SQLite** - Database
