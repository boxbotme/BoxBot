from flask import Flask, render_template, request, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy

from forms import joinForm

from werkzeug.security import generate_password_hash, check_password_hash

import twilio.twiml
import settings

app = Flask(__name__)
app.config.from_object(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/boxbot.db'
db = SQLAlchemy(app)

app.secret_key = settings.secret_key

# Database Setup

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(120))           # Do these need to be unique=True as well?
    lasname = db.Column(db.String(120))
    zipcode = db.Column(db.Integer)
    phonenumber = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(100))
    is_shopper = db.Column(db.Boolean())
    order_status = db.Column(db.Integer)
    product_name = db.Column(db.String(120))
    product_quantity = db.Column(db.Integer)

    def __init__(self, firstname, lastname, zipcode, phonenumber, email, password, is_shopper):
        self.firstname = firstname
        self.lastname = lastname
        self.zipcode = zipcode
        self.phonenumber = phonenumber
        self.email = email
        self.set_password(password)
        self.is_shopper = is_shopper

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User %r>' % self.email

# Page Navigation

@app.route('/')
def index():
    return render_template('index.html')

# Accounts

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if not session.get('signed_in'):
        error = None
        if request.method == 'POST':
            user = User.query.filter_by(email=request.form['email']).first()
            if user is not None:
                email = request.form['email']
                password = request.form['password']
                if email != user.email:
                    error = 'Invalid email address.'
                if user.check_password(password) is False:
                    error = 'Invalid password.'
                else:
                    session['signed_in'] = True
                    session['email'] = user.email
                    session['is_shopper'] = user.is_shopper
                    return redirect('/')
                return render_template('join.html', error=error)
            error = 'Invalid email address.'
        return render_template('signin.html', error=error)
    return redirect('/')

@app.route('/signout')
def signout():
    if session.get('signed_in'):
        session['is_premium'] = False
        session['signed_in'] = False
        return redirect('/')
    return redirect('/')

@app.route('/join', methods=['GET', 'POST'])
def join():
    error = None
    form = joinForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            # User db structure (email, password)
            firstname = form.firstname.data
            lastname = form.lastname.data
            zipcode = form.zipcode.data
            phonenumber = form.phonenumber.data
            email = form.email.data
            password = form.password.data
            user = User(firstname, lastname, zipcode, phonenumber, email, password, False)
            db.session.add(user)
            db.session.commit()
            message = 'You have successfully signed up for BoxBot.'
            session['signed_in'] = True
            session['email'] = user.email
            session['is_shopper'] = user.is_shopper
            return render_template('index.html', message=message)
        error = 'That email is already being used by another account. Please sign in, or use a different email.'
        return render_template('join.html', form=form, error=error)
    return render_template('join.html', form=form)

@app.route('/becomeashopper', methods=['GET', 'POST'])
def become_a_shopper():
    error = None
    form = joinForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            # User db structure (email, password)
            firstname = form.firstname.data
            lastname = form.lastname.data
            zipcode = form.zipcode.data
            phonenumber = form.phonenumber.data
            email = form.email.data
            password = form.password.data
            user = User(firstname, lastname, zipcode, phonenumber, email, password, True)
            db.session.add(user)
            db.session.commit()
            # send_join_email()
            message = 'You have successfully signed up for BoxBot.'
            session['signed_in'] = True
            session['email'] = user.email
            session['is_shopper'] = user.is_shopper
            return render_template('index.html', message=message)
        error = 'That email is already being used by another account. Please sign in, or use a different email.'
        return render_template('becomeashopper.html', form=form, error=error)
    return render_template('becomeashopper.html', form=form)

# Communication

@app.route('/order')
def initial_order_text():
    users = User.query.filter_by(is_shopper=True).all()

    for user in users:
        if user.order_status is 0:
            # make sure to shorten message to ensure SMS does not exceed 160 GSM chars or 70 UCS-2 chars!
            settings.twilio_account_sid = 'secret!'
            settings.twilio_auth_token = 'secret!'
            client = TwilioRestClient(account_sid, auth_token)
            message = client.messages.create( to=user.phonenumber, from='+19723759851', body='Order request from user.firstname. Order details: user.product_name (user.product_quantity) for delivery in two hours. Can you grab this?' )
            user.order_status = 1
            return 'Order successfully placed. You will receive another message upon contact with a personal shopper.'
        else:
            return 'Order was not placed, because you have not yet finished your existing order.'

if __name__ == '__main__':
    app.run(debug=True)
