from datetime import date
import uuid
from sqlalchemy import ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from forms import CreatePostForm, RegisterForm

engine = create_engine("sqlite+pysqlite:///posts.db")


class Base(DeclarativeBase):
    pass


class BlogPost(Base):
    __tablename__ = "blog_posts"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.id"), nullable=False
    )
    author = relationship("User", back_populates="posts", lazy="joined")
    comments = relationship("Comment", back_populates="parent_post", lazy="joined")


class User(Base, UserMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author", lazy="joined")
    comments = relationship("Comment", back_populates="comment_author", lazy="joined")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.id"), nullable=False
    )
    post_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("blog_posts.id"), nullable=False
    )
    comment_author = relationship("User", back_populates="comments", lazy="joined")
    parent_post = relationship("BlogPost", back_populates="comments", lazy="joined")


def create_tables():
    Base.metadata.create_all(engine)


def get_users():
    with Session(engine) as session:
        result = session.query(User)
        users = result.all()
        return users


def get_user(id: str):
    with Session(engine) as session:
        user = session.get(User, id)
        return user


def get_user_by_email(email: str):
    with Session(engine) as session:
        user = session.query(User).where(User.email == email).first()
        return user


def register_user(form: RegisterForm):
    with Session(engine) as session:
        email = form.email.data
        check_email = session.query(User).filter_by(email=email).first()

        if check_email:
            raise ValueError("Email already taken. Please try another.")

        password = str(form.password.data)
        hashed_password = generate_password_hash(
            password, method="pbkdf2:sha256", salt_length=8
        )

        new_user = User(
            id=str(uuid.uuid1()),
            email=email,
            password=hashed_password,
            name=form.name.data,
        )
        session.add(new_user)
        session.commit()
        return new_user


def get_posts():
    with Session(engine) as session:
        result = session.query(BlogPost)
        posts = result.all()
        return posts


def get_post(post_id):
    with Session(engine) as session:
        post = session.get(BlogPost, post_id)
        return post


def add_post(form: CreatePostForm, current_user_id: str):
    with Session(engine) as session:
        new_post = BlogPost(
            id=str(uuid.uuid1()),
            title=form.title.data,
            subtitle=form.subtitle.data,
            img_url=form.img_url.data,
            author_id=current_user_id,
            body=form.body.data,
            date=date.today().strftime("%B %d, %Y"),
        )
        session.add(new_post)
        session.commit()
        return new_post


def change_post(post_id: str, form: CreatePostForm):
    with Session(engine) as session:
        post = session.get(BlogPost, post_id)
        if not post:
            raise ValueError("Post not found")
        post.title = str(form.title.data)
        post.subtitle = str(form.subtitle.data)
        post.img_url = str(form.img_url.data)
        post.body = str(form.body.data)
        session.commit()
        return post


def remove_post(post_id: str):
    with Session(engine) as session:
        post = session.get(BlogPost, post_id)
        if not post:
            raise ValueError("Post not found")
        session.delete(post)
        session.commit()
        return post


def create_comment(comment_text: str, post_id: str, user_id: str):
    with Session(engine) as session:
        new_comment = Comment(
            id=str(uuid.uuid1()),
            comment_text=comment_text,
            author_id=user_id,
            post_id=post_id,
        )
        session.add(new_comment)
        session.commit()
        return new_comment


def get_user_by_id(user_id: str):
    with Session(engine) as session:
        user = session.get(User, user_id)
        return user
