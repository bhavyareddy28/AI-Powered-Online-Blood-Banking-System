# AI-Powered Online Blood Banking and Smart Donor Matching System

## About the Project

The AI-Powered Online Blood Banking and Smart Donor Matching System is a web-based application developed to simplify blood donation and blood request management. It helps users find suitable blood donors, manage blood requests, maintain blood inventory, and predict blood demand using Machine Learning.

## Features

- User and Admin Login
- Donor Registration
- Online Blood Requests
- Smart Donor Matching
- Blood Group Compatibility Checking
- Donor Availability and Eligibility Checking
- Blood Inventory Management
- Admin Dashboard
- Blood Request Approval and Rejection
- Blood Demand Prediction Using Machine Learning
- Notification System

## Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** MySQL
- **Machine Learning:** Scikit-learn, Random Forest Regressor

## Algorithms Used

### Smart Donor Matching

The system uses a rule-based scoring mechanism to rank eligible donors.

- Matching blood group: 60 points
- Matching city: 30 points
- Donor availability: 10 points

The system also checks blood group compatibility and donor eligibility based on the last donation date.

### Blood Demand Prediction

A Random Forest Regressor is used to predict estimated blood demand based on the input features available in the trained model.

## Installation and Setup

### 1. Clone the Repository



```bash
git clone https://github.com/bhavyareddy28/AI-Powered-Online-Blood-Banking-System.git
cd AI-Powered-Online-Blood-Banking-System
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Database

- Start MySQL Server.
- Create the `blood_bank` database.
- Set up the required database tables using the SQL script provided in the repository.
- Configure your local database credentials securely.

### 5. Run the Application

```bash
python app.py
```

Open the following URL in your browser:

`http://127.0.0.1:5000`



## Future Enhancements

- SMS and Email Notifications
- Location-Based Donor Search
- Improved Blood Demand Prediction
- Secure Cloud Deployment
- Enhanced Reporting and Analytics

## Disclaimer

This project is developed for academic purposes. Blood compatibility, donor eligibility, and demand predictions must be verified before real-world use. The application does not replace professional medical advice or authorized blood-bank procedures.
