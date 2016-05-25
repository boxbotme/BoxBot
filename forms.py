from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, PasswordField, SubmitField, validators


class joinForm(Form):
    firstname = TextField('First Name', [validators.Required('Name is required')])
    lastname = TextField('Last Name', [validators.Required('Name is required')])
    zipcode = TextField('Zip Code', [validators.Required('Zip Code is required')])
    phonenumber = TextField('Phone Number', [validators.Required('Phone number is required')])
    email = TextField('Email', [validators.Required('Email is required')])
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match.')
    ])
    confirm = PasswordField('Confirm Password')
    accept_tos = BooleanField('I accept the', [validators.Required('You must accept the terms and conditions.')])
    submit = SubmitField('Create Account')
