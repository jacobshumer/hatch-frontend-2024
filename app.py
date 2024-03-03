from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)


#Dataset of allowed users
allowed_users = {
    'user1': {'password': 'password1', 'email': 'user1@example.com', 'tfa': 'Phone Number', 'tfaAnswer': '1231231233'},
    'user2': {'password': 'password2', 'email': 'user2@example.com', 'tfa': 'Phone Number', 'tfaAnswer': '1231231233'}
}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    response = requests.get('http://localhost:5000', data={"username": username, "password": password})
    if response.status_code == 200:
        return redirect(urlfor)
    if username in allowed_users and allowed_users[username]['password'] == password:
        # Authentication successful, redirect to the next page
        return redirect(url_for('dashboard', username=username))
    else:
        # Authentication failed, redirect back to the sign-in page
        return redirect(url_for('home'))


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
    app.run(debug=True)
