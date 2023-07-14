from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
gravatar = Gravatar(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.String(250), db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class Comment(UserMixin,db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()

    # # admin
    # user = User()
    # user.id = 1
    # user.password = generate_password_hash("1234")
    # user.name = "Priyanshu"
    # user.email = "fhdgh@fhg.com"
    # db.session.add(user)
    #
    # # blog-reader user (not admin)
    # user1 = User()
    # user1.password = generate_password_hash("sdhff")
    # user1.name = "Hello World"
    # user1.email = "qwerty@fhg.com"
    # db.session.add(user1)
    #
    # post = BlogPost()
    # post.title = "The Life of Cactus"
    # post.id = 1
    # post.author_id = 1
    # post.subtitle = "Who knew that cacti lived such interesting lives."
    # post.date = "October 20, 2020"
    # post.body = "<p>Nori grape silver beet broccoli kombu beet greens fava bean potato quandong celery.</p>" \
    #             "<p>Bunya nuts black-eyed pea prairie turnip leek lentil turnip greens parsnip.</p>" \
    #             "<p>Sea lettuce lettuce water chestnut eggplant winter purslane fennel azuki bean earthnut pea sierra " \
    #             "leone bologi leek soko chicory celtuce parsley j&iacute;cama salsify.</p>"
    # post.img_url = "https://images.unsplash.com/photo-1530482054429-cc491f61333b?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=1651&q=80"
    #
    # db.session.add(post)
    # db.session.commit()


# ADMIN: email- fhdgh@fhg.com    password - 1234
# only admin can create and delete posts


def admin_only(func):
    @wraps(func)
    def check_admin(*args, **kwargs):
        if current_user and current_user.get_id() == '1':
            return func(*args, **kwargs)
        else:
            return abort(403)
    return check_admin
#
# def admin_only(f):
#     def decorated_function(*args, **kwargs):
#         if current_user.id != 1:
#             return abort(403)
#         return f(*args, **kwargs)
#     return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated,
                           user_id=current_user.get_id())


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User()
        new_user.name = form.data.get('name')
        new_user.email = form.data.get('email')
        new_user.password = generate_password_hash(form.data.get('password'))

        try:
            db.session.add(new_user)
            db.session.commit()
        except:
            flash('You have already reigstered. Please Login.')
            return redirect(url_for('login'))

        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.data.get('email')
        password = form.data.get('password')

        try:
            user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one()
        except:
            flash('Email does not exist. Please try again.')
            return redirect(url_for('login'))

        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("Incorrect Password. Please try again.")
            return redirect(url_for('login'))

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        if current_user and current_user.is_authenticated:
            new_comm = Comment()
            new_comm.post_id = post_id
            new_comm.author_id = current_user.get_id()
            new_comm.text = form.body.data
            print(form.body.data)

            db.session.add(new_comm)
            db.session.commit()
            print("redirecting to show_post")
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash('You need to login or register to comment')
            return redirect(url_for('login'))

    requested_post = BlogPost.query.get(post_id)
    with app.app_context():
        comments = db.session.execute(db.select(Comment).filter_by(post_id=post_id)).scalars()
        comms = [(comment.text, comment.comment_author.name) for comment in comments]
        for comment in comments:
            print(f'Inside for: {comment.text}   {comment.comment_author.name}')
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, form=form,
                           comments=comms, user_id=current_user.get_id())


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
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
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, is_edit=False, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
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
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
