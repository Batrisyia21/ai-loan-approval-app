import pandas as pd
import numpy as np
import joblib
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- INITIALIZE EXTENSIONS ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'  
login_manager.login_message_category = 'info'

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='user')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- LOAD ML MODELS ---
try:
    model = joblib.load('xgboost_loan_model.pkl')
    encoders = joblib.load('label_encoders.pkl')
    print("✅ AI Models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading AI models: {e}")

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST']) # Added methods here
def login_page():
    """ The Login Form Page """
    if request.method == 'POST':
        # This handles the actual login logic if the form posts to /login
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'predict_page'))
        
        flash('Login failed. Please check your credentials.', 'danger')
        return redirect(url_for('login_page'))

    # If it's a GET request, just show the page
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard' if current_user.role == 'admin' else 'predict_page'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already taken!', 'danger')
            return redirect(url_for('signup'))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        role = 'admin' if username.lower() == 'admin' else 'user'
        
        new_user = User(username=username, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login_page'))
    return render_template('register.html')

@app.route('/auth_login', methods=['POST'])
def auth_login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        flash(f'Welcome back, {username}!', 'success')
        return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'predict_page'))
    
    flash('Login failed. Please check your credentials.', 'danger')
    return redirect(url_for('login_page'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- ADMIN DASHBOARD & ACTIONS ---

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('predict_page'))

    search_query = request.args.get('search', '')
    csv_path = 'loanapproval.csv'
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if search_query:
            df = df[df['applicant_id'].astype(str).str.contains(search_query)]
        
        total = len(df)
        approved = int(df['loan_approved'].sum())
        rejected = total - approved
        # Show last 20 records
        applications = df.tail(20).iloc[::-1].to_dict(orient='records')
    else:
        total, approved, rejected, applications = 0, 0, 0, []

    return render_template('admin.html', total=total, approved=approved, 
                           rejected=rejected, applications=applications, search_query=search_query)

@app.route('/delete/<int:id>')
@login_required
def delete_entry(id):
    if current_user.role != 'admin':
        return redirect(url_for('predict_page'))
    
    csv_path = 'loanapproval.csv'
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df = df[df['applicant_id'] != id] # Keep everything EXCEPT this ID
        df.to_csv(csv_path, index=False)
        flash(f'Application #{id} has been deleted.', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export')
@login_required
def export_csv():
    if current_user.role != 'admin':
        return redirect(url_for('predict_page'))
    
    csv_path = 'loanapproval.csv'
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True, download_name='LendSafe_Report_2026.csv')
    flash("No report found.", "warning")
    return redirect(url_for('admin_dashboard'))

# --- PREDICTION LOGIC ---

@app.route('/predict')
@login_required
def predict_page():
    return render_template('prediction.html')

@app.route('/submit_prediction', methods=['POST'])
@login_required
def submit_prediction():
    try:
        raw_data = {
            'age': float(request.form.get('age')),
            'gender': request.form.get('gender'),
            'marital_status': request.form.get('marital_status'),
            'annual_income': float(request.form.get('annual_income')),
            'loan_amount': float(request.form.get('loan_amount')),
            'credit_score': float(request.form.get('credit_score')),
            'num_dependents': float(request.form.get('num_dependents')),
            'existing_loans_count': float(request.form.get('existing_loans_count')),
            'employment_status': request.form.get('employment_status')
        }

        # Encoding
        gender_enc = encoders['gender'].transform([raw_data['gender']])[0]
        marital_enc = encoders['marital_status'].transform([raw_data['marital_status']])[0]
        employ_enc = encoders['employment_status'].transform([raw_data['employment_status']])[0]

        X_input = pd.DataFrame([{
            'age': raw_data['age'], 'gender': gender_enc, 'marital_status': marital_enc,
            'annual_income': raw_data['annual_income'], 'loan_amount': raw_data['loan_amount'],
            'credit_score': raw_data['credit_score'], 'num_dependents': raw_data['num_dependents'],
            'existing_loans_count': raw_data['existing_loans_count'], 'employment_status': employ_enc
        }])

        prediction = int(model.predict(X_input)[0])
        probability = model.predict_proba(X_input)[0][1] * 100

        # Save to CSV
        csv_path = 'loanapproval.csv'
        file_exists = os.path.exists(csv_path)
        if file_exists:
            df_existing = pd.read_csv(csv_path)
            new_id = 1 if df_existing.empty else int(df_existing['applicant_id'].max() + 1)
        else:
            new_id = 1

        new_entry = {'applicant_id': new_id, **raw_data, 'loan_approved': prediction}
        df_new = pd.DataFrame([new_entry])
        df_new.to_csv(csv_path, mode='a', index=False, header=not file_exists)

        result_text = "Approved" if prediction == 1 else "Rejected"
        return render_template('prediction.html', 
                               prediction_text=result_text, 
                               prediction_class=result_text, 
                               confidence=round(probability, 2))
                               
    except Exception as e:
        return f"System Error: {str(e)}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)