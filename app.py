from flask import Flask, render_template, request, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy

from forms import joinForm

from werkzeug.security import generate_password_hash, check_password_hash

from twilio.rest import TwilioRestClient
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

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    shopper_user_id = db.Column(db.Integer())
    product = db.Column(db.String(50))
    quantity = db.Column(db.Integer())
    status = db.Column(db.String(10))       # pending, in-transit, delivered, received

    def __init__(self, customer_user_id, shopper_user_id, product, quantity):
        self.customer_user_id = customer_user_id
        self.shopper_user_id = shopper_user_id
        self.product = product
        self.quantity = quantity
        self.status = 'pending'

    def __repr__(self):
        return (self.product + " " + self.quantity + " " + self.status)

def send_text(to, body):
    client = TwilioRestClient(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(body=body, to_=to, from_='+19723759851')
    return True

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
                elif user.check_password(password) is False:
                    error = 'Invalid password.'
                else:
                    session['signed_in'] = True
                    session['firstname'] = user.firstname
                    session['email'] = user.email
                    session['phonenumber'] = user.phonenumber
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
            session['firstname'] = user.firstname
            session['email'] = user.email
            session['phonenumber'] = user.phonenumber
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
def newOrder():
    user = User.query.filter_by(email=session.get('email')).first()
    personal_shoppers = User.query.filter_by(is_shopper=True).all()
    message = ''

    for shopper in personal_shoppers:
        #if user.order_status is 0:
            # make sure to shorten message to ensure SMS does not exceed 160 GSM chars or 70 UCS-2 chars!
        '''
        Comment out test values for use in production, and add parameters to method header.

        self.product = product
        self.quantity = quantity
        '''
        product = 'Test Product'
        quantity = 2

        if quantity > 1:
            product += 's'

        myOrder = Order(user.id, shopper.id, product, quantity)
        db.session.add(myOrder)
        db.session.commit()

        # Send personal shopper outreach message
        send_text(shopper.phonenumber, session.get('firstname') + ' needs ' + str(quantity) + ' ' + product + ' for delivery in one hour. Can you grab this? Respond Yes or No.')

        # Send customer confirmation message
        send_text(session.get('phonenumber'), 'Your order is being processed! We\'ll update you as your status changes regarding your ' + str(quantity) + ' ' + product + '. Let us know if there\'s an issue. Happy shopping!')

        '''
        REPLIES WE NEED TO HANDLE

        Customer: Cancelling
        Personal shopper: Invite Decline, Invite Accept
        '''

        message = 'Order successful. We will update you as your delivery status changes.'
    return render_template('index.html', message=message)
    #else:
        #return 'Order was not placed, because you have not yet finished your existing order.'
    #return 'None'

@app.route('/twilio', methods=['POST'])
def twilio():
    form = joinForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(phonenumber=form.From.data).first()
        msg = form.Body.data
        if user is not None:
            order = Order.query.filter_by(user_id=user.id).first()
            if user.is_shopper:
                if user.id is order.user_id:
                    status = order.status
                    if status is 'pending' and 'yes' in msg.lower():
                        status = 'in-transit'
                        # respond to customer
                        cust_message="Your personal shopper " + user.firstname + " will be shopping for you today. Stay tuned!"
                        # respond to shopper
                        shpr_message="Thanks! When you're done, just reply with DELIVERED."
                    elif status is 'in-transit' and 'delivered' in msg.lower():
                        status = 'delivered'
                        # respond to customer
                        cust_message="Your personal shopper has delivered! When you've received your items, confirm delivery by replying RECEIVED."
                        # respond to shopper
                        shpr_message="Great job. Waiting for customer to confirm delivery."
            else:
                if user.id is order.user.id:
                    status = order.status
                    if status is 'delivered' and 'received' in msg.lower():
                        status = 'received'
                        # respond to shopper
                        shpr_message="Your customer has confirmed they've received their desired items. Thanks for delivering!"
                        # respond to customer
                        cust_message="We hope you enjoyed your BoxBot experience and we hope you'll shop with us next time :)"
            send_text(User.query.filter_by(user_id=order.customer_user_id).first().phonenumber, cust_message)
            send_text(User.query.filter_by(user_id=order.shopper_user_id).first().phonenumber, shpr_message)

if __name__ == '__main__':
    app.run(debug=True)
