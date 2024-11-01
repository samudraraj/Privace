from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory
import os
import subprocess

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['THUMBNAIL_FOLDER'] = 'thumbnails/'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit

# Ensure the upload and thumbnail folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['THUMBNAIL_FOLDER'], exist_ok=True)

# Dummy view count storage
view_counts = {}

# Function to create a thumbnail using ffmpeg
def create_thumbnail(video_path, thumbnail_path):
    command = [
        'ffmpeg', '-i', video_path,
        '-ss', '00:00:01', '-vframes', '1', '-s', '160x90',
        '-f', 'image2', thumbnail_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# HTML templates and styles in a single script
HTML_INDEX = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Public Video Upload Site</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        h1, h2 { text-align: center; color: #ffffff; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
        a { text-decoration: none; color: #90caf9; }
        a:hover { color: #64b5f6; }
        .video-list { list-style-type: none; padding: 0; display: flex; flex-direction: column; gap: 10px; }
        .video-item { display: flex; align-items: center; padding: 10px; border: 1px solid #333; border-radius: 5px; transition: background-color 0.3s; }
        .video-item:hover { background-color: #2e2e2e; }
        .thumbnail { width: 160px; height: 90px; border-radius: 5px; margin-right: 10px; }
        .upload-btn { display: inline-block; padding: 10px 20px; background-color: #90caf9; color: #121212; border-radius: 5px; text-align: center; font-size: 16px; transition: background-color 0.3s; }
        .upload-btn:hover { background-color: #64b5f6; }
        footer { text-align: center; padding: 10px; margin-top: 20px; color: #777; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Public Video Upload Site</h1>
        <a href="{{ url_for('upload') }}" class="upload-btn">Upload Video</a>
        <h2>Uploaded Videos</h2>
        <ul class="video-list">
            {% for video in videos %}
                <li class="video-item">
                    <img class="thumbnail" src="{{ url_for('thumbnails', filename=video[:-4] + '.jpg') }}" alt="Thumbnail">
                    <a href="{{ url_for('video', filename=video) }}">{{ video }}</a>
                    <span>{{ view_counts.get(video, 0) }} views</span>
                </li>
            {% endfor %}
        </ul>
    </div>
    <footer>&copy; 2023 Public Video Upload Site</footer>
</body>
</html>
"""

HTML_UPLOAD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Video</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 500px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
        h1 { text-align: center; color: #ffffff; }
        form { display: flex; flex-direction: column; gap: 10px; }
        input[type="file"] { padding: 8px; background-color: #333; color: #e0e0e0; border: none; border-radius: 5px; }
        button { padding: 10px; background-color: #90caf9; color: #121212; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; transition: background-color 0.3s; }
        button:hover { background-color: #64b5f6; }
        a { text-align: center; color: #90caf9; text-decoration: none; margin-top: 10px; }
        a:hover { color: #64b5f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload Video</h1>
        <form action="" method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept="video/*" required>
            <button type="submit">Upload</button>
        </form>
        <a href="{{ url_for('index') }}">Back to Home</a>
    </div>
</body>
</html>
"""

HTML_VIDEO = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ filename }}</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1e1e1e; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
        h1 { color: #ffffff; text-align: center; }
        video { max-width: 100%; border-radius: 10px; margin-top: 20px; }
        p { text-align: center; font-size: 18px; color: #bbb; }
        a { text-align: center; display: block; color: #90caf9; text-decoration: none; margin-top: 20px; }
        a:hover { color: #64b5f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ filename }}</h1>
        <video controls>
            <source src="{{ url_for('uploads', filename=filename) }}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        <p>This video has been viewed {{ views }} times.</p>
        <a href="{{ url_for('index') }}">Back to Home</a>
    </div>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    videos = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template_string(HTML_INDEX, videos=videos, view_counts=view_counts)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename[:-4] + '.jpg')
            create_thumbnail(os.path.join(app.config['UPLOAD_FOLDER'], filename), thumbnail_path)
            return redirect(url_for('index'))
    return render_template_string(HTML_UPLOAD)

@app.route('/video/<filename>')
def video(filename):
    if filename not in view_counts:
        view_counts[filename] = 0
    view_counts[filename] += 1
    return render_template_string(HTML_VIDEO, filename=filename, views=view_counts[filename])

# Serve video files publicly
@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve thumbnail images publicly
@app.route('/thumbnails/<filename>')
def thumbnails(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)

