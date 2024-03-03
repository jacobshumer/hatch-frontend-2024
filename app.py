import json
import os
from functools import wraps
from io import BytesIO
import numpy as np
import joblib
import pandas as pd
import sklearn
from sklearn import svm, preprocessing
from sklearn.utils import shuffle
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

@app.route('/upload', methods=['POST'])
@is_logged_in
def upload_file():
    if 'file'not in request.files:
        return 'No file part'

    file = request.files['file']


    clf = joblib.load('tumor_class_mapping.pkl')

    dp = pd.read_csv("data.csv", index_col=0)  # test
    var = 'cgc_sample_sample_type'
    tumor_stage_mapping = {0: 'Primary Tumor', 1: 'Solid Tissue Normal', 2: 'Recurrent Tumor'}
    if dp[var].dtype != 'int':
        if var in tumor_stage_mapping.values():
            dp[var] = dp[var].map({v: k for k, v in tumor_stage_mapping.items()})
    for column in dp.columns:
        if dp[column].dtype != 'int':
            dp[column] = dp[column].astype("category").cat.codes

    dp = sklearn.utils.shuffle(dp)
    dp = dp.dropna()
    Xp = dp.drop(var, axis=1).values
    Xp = preprocessing.scale(Xp)
    Yp = dp[var].values

    x_test = Xp  # [:-test_size]
    y_test = Yp  # [:-test_size:]

    numcor = 0
    numin = 0
    for X, y in zip(x_test, y_test):
        prediction = clf.predict([X])[0]
        rounded = int(np.round(prediction))
        og = tumor_stage_mapping.get(rounded, "Unknown")
        ogact = tumor_stage_mapping.get(y, "Unknown")
        # print(original_value)
        # print(f"Model: {prediction}, Actual:{y} ")
        print(f"Model: {rounded}, Original Value: {og}, Actual: {ogact}")
        if og == ogact:
            numcor += 1
        else:
            numin += 1
    total = numcor + numin
    percor = (numcor / total) * 100
    print(f"Percent correct: {percor}")

@app.route('/logout', methods=['GET'])
@is_logged_in
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    # app.secret_key = config.secret_key
    print('Starting...')
    app.run(debug=True, port=config['flask_port'])
