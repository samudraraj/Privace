from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flash messages
app.config['UPLOAD_FOLDER'] = 'images/'  # Directory for image uploads
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'  # Database configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize rate limiter
limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database model for posts
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy=True)
    password = db.Column(db.String(100), nullable=False)  # Password for deletion

# Database model for comments
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(100), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    replies = db.relationship('Reply', backref='comment', lazy=True)

# Database model for replies to comments
class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(100), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create the database
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
@limiter.limit("10 per minute")  # Limit homepage views to 10 per minute
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template_string(HTML_INDEX, posts=posts)

@app.route('/post/<int:post_id>')
@limiter.limit("10 per minute")  # Limit post views to 10 per minute
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template_string(HTML_VIEW_POST, post=post)

@app.route('/create', methods=['GET', 'POST'])
@limiter.limit("3 per minute")  # Limit post creation to 3 per minute
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form.get('content')
        password = request.form['password']
        
        # Character limit check
        if len(content) > 200:
            flash("Post content must be 200 characters or fewer.", "error")
            return redirect(url_for('create_post'))

        image_file = request.files.get('image')
        image_filename = None
        if image_file:
            image_filename = image_file.filename
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        new_post = Post(title=title, content=content, image_filename=image_filename, password=password)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template_string(HTML_CREATE_POST)

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@limiter.limit("5 per minute")  # Limit comments to 5 per minute per post
def add_comment(post_id):
    content = request.form['content']
    
    # Character limit check
    if len(content) > 200:
        flash("Comment content must be 200 characters or fewer.", "error")
        return redirect(url_for('view_post', post_id=post_id))

    image_file = request.files.get('image')
    image_filename = None
    if image_file:
        image_filename = image_file.filename
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    new_comment = Comment(content=content, image_filename=image_filename, post_id=post_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/add_reply/<int:comment_id>', methods=['POST'])
@limiter.limit("5 per minute")  # Limit replies to 5 per minute per comment
def add_reply(comment_id):
    content = request.form['content']
    
    # Character limit check
    if len(content) > 200:
        flash("Reply content must be 200 characters or fewer.", "error")
        comment = Comment.query.get_or_404(comment_id)
        return redirect(url_for('view_post', post_id=comment.post_id))

    image_file = request.files.get('image')
    image_filename = None
    if image_file:
        image_filename = image_file.filename
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    new_reply = Reply(content=content, image_filename=image_filename, comment_id=comment_id)
    db.session.add(new_reply)
    db.session.commit()
    comment = Comment.query.get_or_404(comment_id)
    return redirect(url_for('view_post', post_id=comment.post_id))

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    password = request.form['password']
    if password == post.password:
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted successfully.", "success")
        return redirect(url_for('index'))
    else:
        flash("Incorrect password. Post not deleted.", "error")
        return redirect(url_for('view_post', post_id=post_id))

@app.route('/images/<filename>')
def images(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# HTML templates
HTML_INDEX = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Text & Image Posts</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; }
        h1, h2 { text-align: center; color: #ffffff; }
        .post-list { list-style-type: none; padding: 0; }
        .post-item { padding: 20px; background-color: #2e2e2e; border-radius: 10px; margin-bottom: 10px; cursor: pointer; }
        .post-item img { max-width: 100%; height: auto; border-radius: 5px; }
        .upload-btn { display: block; margin: 10px auto; padding: 10px 20px; background-color: #90caf9; color: #121212; border-radius: 5px; text-align: center; }
        .upload-btn:hover { background-color: #64b5f6; }
        footer { text-align: center; padding: 10px; margin-top: 20px; color: #777; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Post Your Thoughts</h1>
        <a href="{{ url_for('create_post') }}" class="upload-btn">Create New Post</a>
        <h2>Posts</h2>
        <ul class="post-list">
            {% for post in posts %}
                <li class="post-item" onclick="window.location='{{ url_for('view_post', post_id=post.id) }}'">
                    <h3>{{ post.title }}</h3>
                    <p>{{ post.content }}</p>
                    {% if post.image_filename %}
                        <img src="{{ url_for('images', filename=post.image_filename) }}" alt="Post Image">
                    {% endif %}
                    <small>Posted on {{ post.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</small>
                </li>
            {% endfor %}
        </ul>
    </div>
    <footer>&copy; 2023 Text & Image Posts</footer>
</body>
</html>
"""

HTML_VIEW_POST = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ post.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 800        px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; }
        h1, h2 { text-align: center; color: #ffffff; }
        .comment-list { list-style-type: none; padding: 0; }
        .comment-item { padding: 10px; background-color: #2e2e2e; border-radius: 5px; margin-bottom: 10px; }
        .reply-list { list-style-type: none; padding-left: 20px; }
        .reply-item { padding: 5px; background-color: #3e3e3e; border-radius: 5px; margin-bottom: 5px; }
        .form-group { margin: 10px 0; }
        .upload-btn { display: inline-block; padding: 10px 20px; background-color: #90caf9; color: #121212; border-radius: 5px; cursor: pointer; }
        .upload-btn:hover { background-color: #64b5f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ post.title }}</h1>
        <p>{{ post.content }}</p>
        {% if post.image_filename %}
            <img src="{{ url_for('images', filename=post.image_filename) }}" alt="Post Image">
        {% endif %}
        <h2>Comments</h2>
        <ul class="comment-list">
            {% for comment in post.comments %}
                <li class="comment-item">
                    <p>{{ comment.content }}</p>
                    {% if comment.image_filename %}
                        <img src="{{ url_for('images', filename=comment.image_filename) }}" alt="Comment Image" style="max-width: 100px;">
                    {% endif %}
                    <small>Commented on {{ comment.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</small>
                    <h3>Replies</h3>
                    <ul class="reply-list">
                        {% for reply in comment.replies %}
                            <li class="reply-item">
                                <p>{{ reply.content }}</p>
                                {% if reply.image_filename %}
                                    <img src="{{ url_for('images', filename=reply.image_filename) }}" alt="Reply Image" style="max-width: 50px;">
                                {% endif %}
                                <small>Replied on {{ reply.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</small>
                            </li>
                        {% endfor %}
                    </ul>
                    <form action="{{ url_for('add_reply', comment_id=comment.id) }}" method="POST">
                        <div class="form-group">
                            <input type="text" name="content" required placeholder="Reply..." maxlength="200">
                            <input type="file" name="image">
                        </div>
                        <button type="submit" class="upload-btn">Add Reply</button>
                    </form>
                </li>
            {% endfor %}
        </ul>
        <form action="{{ url_for('add_comment', post_id=post.id) }}" method="POST">
            <div class="form-group">
                <input type="text" name="content" required placeholder="Add a comment..." maxlength="200">
                <input type="file" name="image">
            </div>
            <button type="submit" class="upload-btn">Add Comment</button>
        </form>
        <form action="{{ url_for('delete_post', post_id=post.id) }}" method="POST">
            <div class="form-group">
                <input type="password" name="password" required placeholder="Delete Post Password">
            </div>
            <button type="submit" class="upload-btn">Delete Post</button>
        </form>
    </div>
</body>
</html>
"""

HTML_CREATE_POST = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Create New Post</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; }
        h1 { text-align: center; }
        .form-group { margin: 10px 0; }
        .upload-btn { display: block; margin: 10px auto; padding: 10px 20px; background-color: #90caf9; color: #121212; border-radius: 5px; }
        .upload-btn:hover { background-color: #64b5f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Create New Post</h1>
        <form action="{{ url_for('create_post') }}" method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <input type="text" name="title" required placeholder="Post Title" maxlength="100">
            </div>
            <div class="form-group">
                <textarea name="content" required placeholder="Post Content (max 200 characters)" maxlength="200></textarea>
            </div>
            <div class="form-group">
                <input type="file" name="image">
            </div>
            <div class="form-group">
                <input type="password" name="password" required placeholder="Delete Post Password">
            </div>
            <button type="submit" class="upload-btn">Create Post</button>
        </form>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

