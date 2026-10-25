# 🛡️ LendSafe - AI-Powered Loan Approval System

LendSafe is a full-stack Flask web application integrated with an **XGBoost Machine Learning model** to automate and evaluate loan applications instantly. It features secure user authentication, role-based dashboards (Admin & User), real-time probability predictions, and data export capabilities.

---

## 📌 Project Note
> **Note:** This was a group project, but the entire website, backend, and machine learning integration were developed solo by **Me**! 🚀

---

## 🚀 Features

- **AI Loan Prediction:** Instantly predicts whether a loan application should be *Approved* or *Rejected* using an XGBoost classifier with confidence scoring.
- **Role-Based Access Control (RBAC):**
  - **Regular Users:** Can submit loan application details and view prediction results.
  - **Admins:** Have access to an administrative dashboard to monitor metrics, search applicant logs, delete entries, and export reports.
- **Secure Authentication:** Built with Flask-Login and Werkzeug password hashing.
- **Data Persistence:** Uses SQLite for user management and CSV logging for audit trails.

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login, python-dotenv
* **Machine Learning:** XGBoost, Scikit-Learn, Pandas, NumPy, Joblib
* **Frontend:** HTML5, CSS, Jinja2 Templates
* **Deployment Ready:** Gunicorn configuration for production servers

---

## 📁 Project Structure

```text
├── app.py                     # Main Flask application & routes
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── xgboost_loan_model.pkl     # Trained XGBoost ML model
├── label_encoders.pkl         # Categorical feature encoders
├── loanapproval.csv           # Application history log
├── static/                    # Stylesheets and static assets
└── templates/                 # HTML templates (home, login, register, prediction, admin)