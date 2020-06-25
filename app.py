from django.core.checks import messages
from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
import yaml
from functools import wraps
from flask_ckeditor import CKEditor
from flask_mail import Mail,Message
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
from wtforms import validators
import os
import MySQLdb
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
import random
import time
from werkzeug.datastructures import CombinedMultiDict


UPLOAD_FOLDER = 'AuthorsPointProject/media'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


app = Flask(__name__, static_url_path='/static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_HEIGHT'] = 200
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'authorspointhelp'
app.config['MAIL_PASSWORD'] = 'authorspoint123@'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
ckeditor = CKEditor(app)
mail = Mail(app)



# Configure db
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def Home():
    return render_template("Home.html")


@app.route('/About')
def About():
    return render_template("About.html")


@app.route('/Articles')
def Articles():
    return render_template("Articles.html")


@app.route('/Register', methods=['GET', 'POST'])
def Register():
    if request.method == 'POST':
        if request.form['Password1'] != request.form['Password2']:
            flash('Password Should Match', "danger")
            return redirect(url_for('Register'))
        else:
            UserDetails = CombinedMultiDict((request.files, request.form))
            Name = UserDetails['Name']
            Email = UserDetails['Email']
            password = sha256_crypt.encrypt(str(UserDetails.get('Password1')))
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users( Name, Email, password) VALUES(%s, %s , %s)", (Name, Email, password))
            mysql.connection.commit()
            cur.close()
            flash("You have successfully registered!", "success")
            return redirect(url_for('Login'))
    else:
        return render_template("Register.html")


@app.route('/User')
def User():
    cur = mysql.connection.cursor()
    resultValue = cur.execute("SELECT * FROM users")
    if resultValue > 0:
        userDetails = cur.fetchall()
        return render_template('User.html', userDetails=userDetails)


@app.route('/login', methods=['GET', 'POST'])
def Login():
    if request.method == 'POST':
        Name = request.form['Name']
        password_candidate = request.form['Password1']
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE name = %s;", [Name])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['name'] = Name

                flash('You are now logged in', 'success')
                return redirect(url_for('Dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/Dashboard')
@is_logged_in
def Dashboard():
    cur = mysql.connection.cursor()
    Value = cur.execute("SELECT * FROM articles;")
    if Value > 0:
        Articles = cur.fetchall()
        return render_template("DashBoard.html", Articles=Articles)
    return render_template("DashBoard.html")


@app.route('/NewArticle', methods=['GET', 'POST'])
@is_logged_in
def NewArticle():
    if request.method == 'POST':
        ArticleDetails = CombinedMultiDict((request.files, request.form))
        print(request.form)
        print(request.files)
        title = ArticleDetails['title']
        body = ArticleDetails['ckeditor']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title,author,body) VALUES (%s,%s,%s);", (title, session['name'], body))
        mysql.connection.commit()
        cur.close()
        flash("New Article Created!", 'success')
        return redirect(url_for('Dashboard'))
    return render_template("NewArticle.html")


@app.route('/EditArticle/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def EditArticle(id):
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s;", [id])
    if result > 0:
        article = cur.fetchone()
        title = article['title']
        body = article['body']
        cur.close()

        if request.method == 'POST':
            title = request.form['title']
            body = request.form['ckeditor']

            # Create Cursor
            cur = mysql.connection.cursor()
            app.logger.info(title)
            # Execute
            cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s;", (title, body, id))
            # Commit to DB
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash('Article Updated', 'success')
            return redirect(url_for('YourArticles'))
    return render_template("EditArticle.html", Articles=Articles)


@app.route('/DeleteArticle/<string:id>', methods=['POST'])
@is_logged_in
def DeleteArticle(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('Dashboard'))


@app.route('/YourArticles')
@is_logged_in
def YourArticles():
    cur = mysql.connection.cursor()
    Value = cur.execute("SELECT * FROM articles;")
    if Value > 0:
        Articles = cur.fetchall()
        return render_template("YourArticles.html", Articles=Articles)
    else:
        flash("NO ARTICLES FOUND", "danger")
        return redirect(url_for('Dashboard'))


@app.route('/logout')
@is_logged_in
def Logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('Login'))


@app.route('/Help', methods=['GET', 'POST'])
def Help():
    if request.method == 'POST':
        Name = request.form['Name']
        Email = request.form['Email']
        Text = request.form['Message']
        msg = Message('You have a Query from %s' %Name,  sender=Email, recipients=['avishigupta143@gmail.com'])
        msg.body = Text
        msg.subject = "Query from AuthorsPoint"
        mail.send(msg)
        flash("Your Query has been received, you'll be reached out soon!", 'success')
        return redirect(url_for('Home'))
    return render_template("Help.html")


if __name__ == '__main__':
    app.secret_key = 'secret123@'
    app.run(debug=True)
