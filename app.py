import os
import smtplib
from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import (
    login_required,
    login_user,
    LoginManager,
    current_user,
    logout_user,
)
from functools import wraps
from werkzeug.security import check_password_hash
from db_posts import (
    create_comment,
    get_posts,
    get_post,
    add_post,
    change_post,
    get_user_by_email,
    get_user_by_id,
    register_user,
    remove_post,
)

from forms import CommentForm, ContactForm, CreatePostForm, LoginForm, RegisterForm

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(
    app,
    size=100,
    rating="g",
    default="retro",
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None,
)


@login_manager.user_loader
def load_user(user_id):
    user = get_user_by_id(user_id)
    return user


@login_manager.unauthorized_handler
def unauthorized():
    flash("You need to be logged in to access this page.")
    return redirect(url_for("login"))


def admin_only(func):
    @login_required
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.name == "admin":
            return func(*args, **kwargs)
        else:
            flash("Only admin users can create a new post.")
            return redirect(url_for("get_all_posts"))

    return wrapper


def owner_only(func):
    @login_required
    @wraps(func)
    def wrapper(*args, **kwargs):
        post_id = kwargs.get("post_id")
        post = get_post(post_id)
        if not post:
            return
        if post.author.id == current_user.id:
            return func(*args, **kwargs)
        else:
            flash("Only the owner of the post can edit or delete it.")
            return redirect(url_for("get_all_posts"))

    return wrapper


def only_not_logged_in(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            flash("You are already logged in.")
            return redirect(url_for("get_all_posts"))
        else:
            return func(*args, **kwargs)

    return wrapper


@app.route("/register", methods=["GET", "POST"])
@only_not_logged_in
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        try:
            register_user(register_form)
            return redirect(url_for("login"))
        except ValueError as e:
            flash("There was an issue registering your account: " + str(e.args))
    return render_template("register.html", form=register_form)


@app.route("/login", methods=["GET", "POST"])
@only_not_logged_in
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = get_user_by_email(str(login_form.email.data))
        if user:
            if check_password_hash(user.password, str(login_form.password.data)):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Password incorrect, please try again.")
        else:
            flash("That email does not exist, please try again or register.")
    return render_template("login.html", form=login_form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("get_all_posts"))


@app.route("/")
def get_all_posts():
    posts = get_posts()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route("/post/<post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        try:
            create_comment(
                comment_text=str(comment_form.comment_text.data),
                post_id=post_id,
                user_id=current_user.id,
            )
            return redirect(url_for("show_post", post_id=post_id))
        except ValueError as e:
            flash("There was an issue adding your comment: " + str(e.args))
    requested_post = get_post(post_id)
    return render_template(
        "post.html", post=requested_post, form=comment_form, gravatar=gravatar
    )


@app.route("/new-post", methods=["GET", "POST"])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        try:
            add_post(form, current_user.id)
            return redirect(url_for("get_all_posts"))
        except ValueError as e:
            flash("There was an issue adding your post: " + str(e.args))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@owner_only
def edit_post(post_id):
    edit_form = CreatePostForm()
    if edit_form.validate_on_submit():
        try:
            change_post(post_id=post_id, form=edit_form)
            return redirect(url_for("show_post", post_id=post_id))
        except ValueError as e:
            flash("There was an issue editing your post: " + str(e.args))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<post_id>")
@owner_only
def delete_post(post_id):
    try:
        remove_post(post_id)
    except ValueError as e:
        flash("There was an issue deleting your post: " + str(e.__cause__))
    return redirect(url_for("get_all_posts"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    contact_form = ContactForm()
    if contact_form.validate_on_submit():
        password = os.environ.get("EMAIL_PASSWORD")
        email_from = os.environ.get("EMAIL_FROM")
        email_to = os.environ.get("EMAIL_TO")
        msg = (
            f"Name: {contact_form.name.data}\n"
            f"Email: {contact_form.email.data}\n"
            f"Phone: {contact_form.phone.data}\n"
            f"Message: {contact_form.message.data}"
        )
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(user=str(email_from), password=str(password))
            connection.sendmail(
                msg=f"Subject: Python blog contacts\n\n{msg}",
                from_addr=str(email_from),
                to_addrs=str(email_to),
            )
    return render_template("contact.html", form=contact_form)
