from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from models import db, User

app = Flask(__name__)

# app config
app.config['SECRET_KEY'] = "supersecret"
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:ben421343@localhost:5432/dominos_pizza"

db.init_app(app)

# login manager config
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user:
            flash(f'User with username "{username}" already exists', 'danger')
            return render_template('register.html')

        new_user = User(username=username, password=password)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
        else:
            flash("Wrong username or password", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    if not current_user.is_authenticated:
            flash("You are already logged out", "modal-warning")
            return redirect(url_for('home'))
    
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)