from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'images/'  # Directory for image uploads
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'  # Database configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

# Database model for comments
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(100), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create the database
with app.app_context():
    db.create_all()

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
        .container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
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
        .container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
        h1, h2 { text-align: center; color: #ffffff; }
        .post-content { margin-bottom: 20px; }
        .comment-list { list-style-type: none; padding: 0; margin-top: 20px; }
        .comment-item { padding: 10px; background-color: #3e3e3e; border-radius: 5px; margin-top: 10px; }
        a { color: #90caf9; text-decoration: none; }
        a:hover { color: #64b5f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ post.title }}</h1>
        <div class="post-content">
            <p>{{ post.content }}</p>
            {% if post.image_filename %}
                <img src="{{ url_for('images', filename=post.image_filename) }}" alt="Post Image" style="max-width: 100%; height: auto;">
            {% endif %}
            <small>Posted on {{ post.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</small>
        </div>
        <h2>Comments:</h2>
        <ul class="comment-list">
            {% for comment in post.comments %}
                <li class="comment-item">
                    <p>{{ comment.content }}</p>
                    {% if comment.image_filename %}
                        <img src="{{ url_for('images', filename=comment.image_filename) }}" alt="Comment Image" style="max-width: 100%; height: auto;">
                    {% endif %}
                    <small>Commented on {{ comment.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</small>
                </li>
            {% endfor %}
        </ul>
        <form action="{{ url_for('add_comment', post_id=post.id) }}" method="POST" enctype="multipart/form-data">
            <input type="text" name="content" placeholder="Add a comment..." required>
            <input type="file" name="image" accept="image/*">
            <button type="submit">Comment</button>
        </form>
        <a href="{{ url_for('index') }}">Back to Home</a>
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
        .container { max-width: 600px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; }
        h1 { text-align: center; }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ccc; }
        button { padding: 10px 15px; background-color: #90caf9; color: #121212; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background-color: #64b5f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Create New Post</h1>
        <form action="{{ url_for('create_post') }}" method="POST" enctype="multipart/form-data">
            <input type="text" name="title" placeholder="Post Title" required>
            <textarea name="content" placeholder="Post Content" required></textarea>
            <input type="file" name="image" accept="image/*">
            <button type="submit">Submit Post</button>
        </form>
        <a href="{{ url_for('index') }}">Back to Home</a>
    </div>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template_string(HTML_INDEX, posts=posts)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template_string(HTML_VIEW_POST, post=post)

@app.route('/create', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form.get('content')
        image_file = request.files.get('image')
        
        image_filename = None
        if image_file:
            image_filename = image_file.filename
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        new_post = Post(title=title, content=content, image_filename=image_filename)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template_string(HTML_CREATE_POST)

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    content = request.form['content']
    image_file = request.files.get('image')

    image_filename = None
    if image_file:
        image_filename = image_file.filename
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    new_comment = Comment(content=content, image_filename=image_filename, post_id=post_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/images/<filename>')
def images(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


