from flask import Flask, render_template, redirect, flash, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import timedelta


def login_required(f):
    @wraps(f)
    def decorator_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Lütfen Giriş Yapın !", "danger")
            return redirect(url_for("login"))
    return decorator_function


class RegisterForm(Form):
    name = StringField("Ad ve Soyad", validators=[validators.length(min=5,max=30)])
    email = StringField("Email Adresi",validators=[validators.email(message="Mail Adresi Geçersiz.")])
    username = StringField("Kullanıcı Adı", validators=[validators.length(min=5,max=20)])
    password = PasswordField("Parola", validators=[
        validators.data_required("Lütfen Parola Alanını Doldurun!"),
        validators.EqualTo(fieldname="confirm", message="Parolalar Uyuşmuyor.")
    ])

    confirm = PasswordField("Parola Doğrula!")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.length(min=10)])

app = Flask(__name__)
app.static_folder = "static"

app.secret_key = "secret_key"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True


app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "your_database"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.before_request
def session_expired():
    session.modified = True

#INDEX
@app.route("/")
def index():
    return render_template("index.html")

#ABOUT
@app.route("/about")
@login_required
def about():
    return render_template("about.html")

#ARTICLES
@app.route("/articles")
@login_required
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

#ADD ARTICLE
@app.route("/addarticle", methods=["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "insert into articles(title, author, content) VALUES(%s,%s,%s)"
        insert = (title, session["username"], content)
        cursor.execute(sorgu, insert)
        mysql.connection.commit()

        cursor.close()
        flash("Makale başarıyla eklendi", "success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html", form = form)

#EDIT ARTICLE
@app.route("/edit/<string:id>", methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu, (id, session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya yetkiniz yok", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html", form=form)
    else:
        #POST SIDE
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()
        sorguedit = "update articles set title = %s, content = %s where id = %s"
        cursor.execute(sorguedit,(newTitle, newContent, id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi", "success")
        return redirect(url_for("dashboard"))

#DELETE ARTICLE
@app.route("/delete/<string:id>", methods= ["GET","POST"])
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where author = %s and id = %s"
    result = cursor.execute(sorgu, (session["username"],id))

    if result > 0:
         sorgusil = "delete from articles where id = %s"
         cursor.execute(sorgusil, (id,))
         mysql.connection.commit()
         flash("Makale silindi", "secondary")
         return redirect(url_for("dashboard"))
    else:
        flash("Bu makaleyi silmek için yetkiniz yok veya böyle bir makale yok!","danger")
        return redirect(url_for("index"))
        

#DETAIL PAGE
@app.route("/article/<string:id>")
@login_required
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where id = %s"
    result = cursor.execute(sorgu, (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

#DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where author = %s"
    result = cursor.execute(sorgu, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")
    return render_template("dashboard.html")

#REGISTER
@app.route("/register", methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.hash(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = """INSERT INTO users (name,username,email,password) VALUES (%s,%s,%s,%s)"""
        insert = (name, username, email, password)
        cursor.execute(sorgu, insert)
        mysql.connection.commit()
        cursor.close()
        flash("Kayıt olduğunuz için teşekkürler :) ", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form = form)

#LOGIN
@app.route("/login", methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "select * from users where username = %s"
        result = cursor.execute(sorgu, (username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                session["logged_in"] = True
                session["username"] = username
                flash("Giriş başarılı hoşgeldin", "success")
                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir Kullanıcı yoktur.", "warning")
            return redirect(url_for("login"))
    return render_template("login.html", form = form)

#LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış başarılı", "warning")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
