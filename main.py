import secrets

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from models import Order, db, User, Pizza
import datetime

app = Flask(__name__)

# app config
app.config['SECRET_KEY'] = "supersecret"
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:ben421343@localhost:5432/pizzeria"

db.init_app(app)

# login manager config
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.after_request
def apply_csp(response):
    nonce = secrets.token_urlsafe(16)
    csp = (
        f"default-src 'self';"
        f"script-src 'self' 'self' https://cdn.jsdelivr.net 'unsafe-inline' 'nonce-{nonce}';"
        f"style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline';"
        f"img-src 'self' data: https:;"
        f"frame-ancestors 'none';"
        f"base-uri 'self';"
        f"form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    response.set_cookie('nonce', nonce)
    return response

@app.before_request
def ensure_csrf_token():
    session.setdefault('csrf_token', secrets.token_urlsafe(32))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_positions():
    if not Pizza.query.first():
        margherita = Pizza(
            name="Margherita Pizza",
            description="Classic pizza with tomato sauce and mozzarella",
            price=9.99,
            status=True,
            image_url="https://shorturl.at/D4UYa"
        )
        pepperoni = Pizza(
            name="Pepperoni Pizza",
            description="Pizza with pepperoni slices",
            price=12.50,
            status=True,
            image_url="https://shorturl.at/aZZaN"
        )
        mozzarella = Pizza(
            name="Mozarella Pizza",
            description="Cheesy pizza with mozzarella cheese",
            price=14.99,
            status=True,
            image_url="https://shorturl.at/70laB"
        )
        hawaiian = Pizza(
            name="Hawaiian Pizza",
            description="Pizza with ham and pineapple",
            price=15.99,
            status=True,
            image_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"
        )
        four_cheese = Pizza(
            name="Four Cheese Pizza",
            description="Pizza with four types of cheese",
            price=16.99,
            status=True,
            image_url="https://images.unsplash.com/photo-1571407970349-bc81e7e96d47"
        )
        marinara = Pizza(
            name="Marinara Pizza",
            description="Classic pizza with marinara sauce",
            price=13.99,
            status=True,
            image_url="https://images.unsplash.com/photo-1604382354936-07c5d9983bd3"
        )

        db.session.add_all([margherita, pepperoni, mozzarella, hawaiian, four_cheese, marinara])
        db.session.commit()

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.username == 'admin':
            return redirect(url_for('admin_orders'))

        just_placed_order = session.pop('just_placed_order', False)
        order = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_time.desc()).first()
        if order and not just_placed_order:
            if order.status == 'Pending':
                flash("You have a pending order. Please wait for it to be processed.", "info")
            elif order.status == 'Processing':
                flash("Your order is being processed. Please wait.", "info")
            elif order.status == 'Done':
                flash("Your order has been completed. Enjoy your meal!", "success")
            elif order.status == 'Cancelled':
                flash("Your order has been cancelled. Please place a new order.", "danger")
    return render_template('home.html')

@app.route('/menu')
def menu():
    all_positions = Pizza.query.filter_by(status=True).all()
    return render_template('menu.html', items=all_positions)

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
            return redirect(url_for('home'))
        else:
            flash("Wrong username or password", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():    
    logout_user()
    return redirect(url_for('home'))

@app.route('/position/<name>', methods=['GET', 'POST'])
def position(name):
    position = Pizza.query.filter_by(name=name).first()

    if request.method == 'POST':
        if request.form.get('csrf_token') != session.get('csrf_token'):
            return "Request blocked", 403
        elif not current_user.is_authenticated:
            flash("You must be logged in to add items to the cart", "danger")
            return redirect(url_for('position', name=name))
        
        amount = request.form.get('amount')
        size = request.form.get('size') 

        cart = session.get('cart', {})
        
        cart[name] = {
            'amount': amount,
            'size': size,
            'description': position.description,
            'price': position.price
        }
        
        session['cart'] = cart
        flash(f"Added {amount} {size} {name} to cart", "success")
        return redirect(url_for('menu'))

    return render_template('position.html', csrf_token=session.get('csrf_token'), position=position)

@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if not current_user.is_authenticated:
        flash("You must be logged in to view the cart", "danger")
        return redirect(url_for('login'))
    cart = session.get('cart')
    if request.method == 'POST':
        if request.form.get('csrf_token') != session['csrf_token']:
            return "Request blocked", 403

        if not cart:
            flash("Your cart is empty", "danger")
            return redirect(url_for('menu'))

        new_order = Order(order_list=cart, order_time=datetime.datetime.now(), user_id=current_user.id)
        db.session.add(new_order)
        db.session.commit()

        session['just_placed_order'] = True
        session.pop('cart', None)
        flash("Order placed successfully!", "success")
        return redirect(url_for('home'))

    return render_template('cart.html',cart=cart, csrf_token=session['csrf_token'])

@app.route('/remove_item/<name>', methods=['POST'])
@login_required
def remove_item(name):
    if request.form.get('csrf_token') != session.get('csrf_token'):
        return "Request blocked", 403

    cart = session.get('cart', {})
    
    if name in cart:
        cart.pop(name)
        session['cart'] = cart 
        flash(f"{name} was removed from your cart.", "success")
        
    return redirect(url_for('cart'))

@app.route('/admin_orders', methods=['GET', 'POST'])
@login_required
def admin_orders():
    if current_user.username != 'admin':
        flash("You do not have permission to view this page", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')

        if order_id and new_status:
            order = Order.query.get(order_id)
            if order:
                order.status = new_status
                db.session.commit()
                flash(f"Order #{order.id} status updated to {new_status}", "success")

    orders = Order.query.filter(Order.status.in_(['Pending', 'Processing'])).order_by(Order.order_time.desc()).all()
    return render_template('admin_orders.html', orders=orders)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_positions()
    app.run(debug=True)