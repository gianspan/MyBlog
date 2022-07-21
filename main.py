import werkzeug.security
from flask import Flask, render_template, redirect, url_for, flash, request,g,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    # This will act like a List of comments objects attached to each User.
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

db.create_all()

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.get_id() != '1':
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    # print(current_user.get_id())
    return render_template("index.html", all_posts=posts,current_user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    register_form=RegisterForm()
    name = request.form.get('name')
    password = request.form.get('password')
    email = request.form.get('email')

    if register_form.validate_on_submit() and request.method == "POST":
        hashed_password = werkzeug.security.generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        user_selected = User.query.filter_by(email=email).first()
        if not user_selected:
            new_user = User(
                email=request.form.get('email'),
                password=hashed_password,
                name=name)
            db.session.add(new_user)
            db.session.commit()
            # Log in and authenticate user after adding details to database.

            login_user(new_user)
            # print(current_user.get_id())
            # is_auth=werkzeug.security.check_password_hash(hashed_password, password)
            # return render_template("secrets.html", name=name)
            return redirect(url_for('get_all_posts',logged_in=True))
        else:
            flash(u'You have already signed up with that email,login instead!', 'error')
            return render_template("login.html")
    return render_template("register.html",form = register_form,current_user=current_user )


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if request.method == 'POST':
        email_entered=request.form.get('email')
        password_entered=request.form.get('password')
        user_selected=User.query.filter_by(email=email_entered).first()
        is_authorized_user = False
        if user_selected:
            name=user_selected.name
            is_authorized_user = werkzeug.security.check_password_hash(user_selected.password, password_entered)

        if is_authorized_user:
            login_user(user_selected)
            # print(f'fff' + current_user.get_id())
            return redirect(url_for('get_all_posts'))
        elif not user_selected:
            flash(u'The email entered is not valid', 'error')
        else:
            flash(u'The password entered is not correct', 'error')
    return render_template("login.html", form =login_form,current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form=CommentForm()
    login_form=LoginForm()
    requested_post = BlogPost.query.get(post_id)
    comments=Comment.query.filter_by(post_id=post_id).all()
    if form.validate_on_submit() and request.method == "POST":
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.comment.data,
                author_id=int(current_user.get_id()),
                post_id=post_id
            )
            db.session.add(new_comment)
            db.session.commit()
            comments = Comment.query.filter_by(post_id=post_id).all()
        else:
            flash(u'You need to login to comment', 'error')
            return redirect(url_for('login',form =login_form,current_user=current_user))
            # return render_template("login.html",form =login_form,current_user=current_user)
    return render_template("post.html", post=requested_post,current_user=current_user,form=form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html",current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html",current_user=current_user)



@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    # print(f'currnt user1:' + current_user.get_id())
    if form.validate_on_submit() and request.method == "POST":
        print(f'currnt user2:' + current_user.get_id())
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        print(f'currnt user3:' + current_user.get_id())
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,current_user=current_user)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
