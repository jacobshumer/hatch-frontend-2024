import json
import os
from functools import wraps
from io import BytesIO

from flask import Flask, render_template, request, redirect, url_for, session, send_file
import requests

file = open('config.json')
config = json.load(file)
backend_url = f'{config['backend']['protocol']}://{config['backend']['host']}:{config['backend']['port']}'
print(backend_url)

app = Flask(__name__)
app.secret_key = config['secret_key']

# Dataset of allowed users
# allowed_users = {
#    'user1': {'password': 'password1', 'email': 'user1@example.com', 'tfa': 'Phone Number', 'tfaAnswer': '1231231233'},
#    'user2': {'password': 'password2', 'email': 'user2@example.com', 'tfa': 'Phone Number', 'tfaAnswer': '1231231233'}
# }


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        print(session)
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            print('not logged in accessing dashboard page, redirecting to dashboard')
            return redirect(url_for('login'))
    return wrap


def is_not_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        print(session)
        if 'logged_in' in session:
            print('logged in accessing login page, redirecting to dashboard')
            return redirect(url_for('dashboard'))
        else:
            return f(*args, **kwargs)
    return wrap


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
@is_not_logged_in
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Allows the session variables to be set without the backend server running
        print(config)
        if config['debug']:
            session['logged_in'] = True
            session['username'] = username
            session['token'] = 'token'
            print(session)

            return redirect(url_for('dashboard'))

        # Gets the data from the server and uses it to set the session variables (or not)
        res = requests.get(
            f'{backend_url}/authentication',
            data={"username": username, "password": password})
        if res.status_code == 200:
            session['is_logged_in'] = True
            session['username'] = username
            session['token'] = res.json()['token']
            return redirect(url_for('dashboard', username=username))
        else:
            return render_template('error.html', code=res.status_code)

    return render_template('index.html')


@app.route('/dashboard', methods=['GET'])
@is_logged_in
def dashboard():
    if request.method == 'POST':
        count = request.form['count']
        try:
            count = int(count)
        except ValueError:
            return render_template('error.html', code='Please input a number.')

        res = requests.get(
            f'{backend_url}/data',
            data={
                "token": session['token'],
                "count": count
            }
        )

        if res.status_code == 200:
            file_content = BytesIO(res.content)
            return send_file(file_content, as_attachment=True)
        else:
            return render_template('error.html', code=res.status_code)

    return render_template('mainpage.html', username=session['username'])


@app.route('/logout', methods=['GET'])
@is_logged_in
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    # app.secret_key = config.secret_key
    print('Starting...')
    app.run(debug=True, port=config['flask_port'])
