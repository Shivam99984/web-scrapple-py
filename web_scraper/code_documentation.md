# Web Scraper Code Documentation

## app.py
```python
import logging
import io, csv, json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import requests
from bs4 import BeautifulSoup
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure random key

# Configure logging for user activity
logging.basicConfig(filename='usage.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ScheduledJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    selector = db.Column(db.String(255), nullable=False)
    interval = db.Column(db.Integer, nullable=False)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('jobs', lazy=True))

class ScrapingResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scheduled_job_id = db.Column(db.Integer, db.ForeignKey('scheduled_job.id'), nullable=False)
    data = db.Column(db.Text, nullable=False)  # Stored as JSON string
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)

    scheduled_job = db.relationship('ScheduledJob', backref=db.backref('results', lazy=True))

# Helper Functions
def perform_scraping(url, selector):
    """Scrape the provided URL using the CSS selector."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        elements = soup.select(selector)
        results = [element.get_text(strip=True) for element in elements]
        logging.info(f"Scraped URL: {url} with selector: {selector}. Results count: {len(results)}")
        return results
    except Exception as e:
        logging.error(f"Error scraping {url} with selector {selector}: {e}")
        return []

def current_user():
    """Return the logged-in user object or None."""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if username and email and password:
            if User.query.filter_by(username=username).first():
                flash("Username already exists.")
            else:
                user = User(username=username, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Registration successful. Please log in.")
                return redirect(url_for('login'))
        else:
            flash("All fields are required.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash("Logged in successfully.")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.")
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html', user=current_user())

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    selector = request.form.get('selector')
    if not url or not selector:
        return redirect(url_for('index'))
    results = perform_scraping(url, selector)
    return render_template('results.html', url=url, selector=selector, results=results, user=current_user())

@app.route('/export', methods=['POST'])
def export():
    data = request.form.getlist('data')
    export_format = request.form.get('export_format')
    if not data or not export_format:
        return "No data to export or format not specified", 400

    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Scraped Data'])
        for item in data:
            writer.writerow([item])
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name="results.csv"
        )
    elif export_format == 'json':
        json_data = json.dumps(data)
        return send_file(
            io.BytesIO(json_data.encode()),
            mimetype="application/json",
            as_attachment=True,
            download_name="results.json"
        )
    elif export_format == 'xlsx':
        df = pd.DataFrame(data, columns=["Scraped Data"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="results.xlsx"
        )
```

## requirements.txt
```
flask==3.0.0
requests==2.31.0
beautifulsoup4==4.12.2
pandas==2.1.4
selenium==4.15.0   
xlsxwriter==3.1.9
APScheduler==3.10.4    
Flask-SQLAlchemy==3.1.1
Werkzeug==3.1.3
```

## HTML Templates

### base.html
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Web Scraper</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  <script src="{{ url_for('static', filename='element_selector.js') }}"></script>
</head>
<body>
  <div class="container">
    <header>
      <h1>Web Scraper</h1>
      <nav>
        <a href="{{ url_for('index') }}">Home</a>
        <a href="{{ url_for('schedule') }}">Schedule</a>
        <a href="{{ url_for('logs') }}">Logs</a>
      </nav>
    </header>
    
    {% block content %}{% endblock %}
  </div>
</body>
</html>
```

### index.html
```html
{% extends "base.html" %}
{% block content %}
  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}
  <form method="post">
    <label for="url">Website URL:</label>
    <input type="text" id="url" name="url" placeholder="https://example.com" required><br><br>
    <button type="submit">Load Preview</button>
  </form>
{% endblock %}
```

### login.html
```html
{% extends "base.html" %}
{% block content %}
  <h2>Login</h2>
  <form method="post">
    <label for="username">Username:</label>
    <input type="text" id="username" name="username" required><br><br>
    <label for="password">Password:</label>
    <input type="password" id="password" name="password" required><br><br>
    <button type="submit">Login</button>
  </form>
  <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a>.</p>
{% endblock %}
```

### register.html
```html
{% extends "base.html" %}
{% block content %}
  <h2>Register</h2>
  <form method="post">
    <label for="username">Username:</label>
    <input type="text" id="username" name="username" required><br><br>
    <label for="email">Email:</label>
    <input type="email" id="email" name="email" required><br><br>
    <label for="password">Password:</label>
    <input type="password" id="password" name="password" required><br><br>
    <button type="submit">Register</button>
  </form>
  <p>Already have an account? <a href="{{ url_for('login') }}">Log in here</a>.</p>
{% endblock %}
```

### results.html
```html
{% extends "base.html" %}
{% block content %}
  <h2>Results for URL: {{ url }}</h2>
  <p>Using selector: <strong>{{ selector }}</strong></p>
  {% if results %}
    <form method="post" action="{{ url_for('export') }}">
      <ul>
        {% for item in results %}
          <li>{{ item }}</li>
          <!-- Hidden input to send data for export -->
          <input type="hidden" name="data" value="{{ item }}">
        {% endfor %}
      </ul>
      <label for="export_format">Export Format:</label>
      <select name="export_format" id="export_format">
        <option value="csv">CSV</option>
        <option value="json">JSON</option>
        <option value="xlsx">Excel (XLSX)</option>
      </select>
      <button type="submit">Export Data</button>
    </form>
  {% else %}
    <p>No results found using the selector provided.</p>
  {% endif %}
  <br>
  <a href="{{ url_for('index') }}">Back to Home</a>
{% endblock %}
```

### schedule.html
```html
{% extends "base.html" %}
{% block content %}
  <h2>Schedule a Scraping Task</h2>
  {% if message %}
    <p class="message">{{ message }}</p>
  {% endif %}
  <form method="post">
    <label for="url">Website URL:</label>
    <input type="text" id="url" name="url" placeholder="https://example.com" required><br><br>
    
    <label for="selector">CSS Selector:</label>
    <input type="text" id="selector" name="selector" placeholder="e.g. .content, #main" required><br><br>
    
    <label for="scheduled_time">Scheduled Time:</label>
    <input type="datetime-local" id="scheduled_time" name="scheduled_time" required><br><br>
    
    <button type="submit">Schedule Task</button>
  </form>
  
  <h3>Scheduled Jobs</h3>
  {% if jobs %}
    <ul>
    {% for job in jobs %}
      <li>
        {{ job.job_id }}: URL: {{ job.url }}, Selector: {{ job.selector }},
        Scheduled For: {{ job.next_run }}, Created At: {{ job.created_at }}
        <form method="post" action="{{ url_for('delete_job', job_db_id=job.id) }}" style="display:inline;">
          <button type="submit">Remove</button>
        </form>
      </li>
    {% endfor %}
    </ul>
  {% else %}
    <p>No scheduled jobs.</p>
  {% endif %}
{% endblock %}
```

### preview.html
```html
{% extends "base.html" %}
{% block content %}
  <h2>Preview for URL: {{ url }}</h2>
  <p>Click on an element in the preview below to select it for scraping.</p>
  <div id="preview-container" style="border: 1px solid #ccc; padding: 10px;">
    {{ html_content|safe }}
  </div>
  <form method="post" action="{{ url_for('scrape') }}">
    <input type="hidden" name="url" value="{{ url }}">
    <label for="selector">Selected CSS Selector:</label>
    <input type="text" id="selector" name="selector" placeholder="Element selector will appear here" required>
    <button type="submit">Scrape Selected Element</button>
  </form>
{% endblock %}
```

### error.html
```html
{% extends "base.html" %}

{% block title %}Error - Web Scrapple{% endblock %}

{% block content %}
<div class="error-container">
    <div class="error-content">
        <h2>{{ error_title|default('Oops! Something went wrong') }}</h2>
        <p class="error-message">{{ error_message }}</p>
        <div class="error-actions">
            <a href="{{ url_for('index') }}" class="button primary">Return Home</a>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_css %}
<style>
    .error-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 60vh;
        text-align: center;
    }

    .error-content {
        max-width: 600px;
        padding: 2rem;
    }

    .error-message {
        margin: 1.5rem 0;
        color: #666;
    }

    .error-actions {
        margin-top: 2rem;
    }
</style>
{% endblock %}
```

## Static Files

### style.css
```css
body {
    font-family: Arial, sans-serif;
    background-color: #f7f7f7;
    margin: 0;
    padding: 0;
}
.container {
    width: 80%;
    margin: auto;
    overflow: hidden;
    padding: 20px;
}
h1, h2 {
    text-align: center;
    color: #333;
}
nav {
    text-align: center;
    margin-bottom: 20px;
}
nav a {
    margin: 0 10px;
    text-decoration: none;
    color: #333;
}
form {
    margin: 20px auto;
    width: 80%;
    background: #fff;
    padding: 20px;
    border-radius: 5px;
}
input[type="text"], input[type="number"] {
    width: 100%;
    padding: 10px;
    margin: 5px 0 15px 0;
    border: 1px solid #ccc;
    border-radius: 3px;
}
button {
    display: block;
    width: 100%;
    padding: 10px;
    background: #333;
    color: #fff;
    border: none;
    border-radius: 3px;
    cursor: pointer;
}
button:hover {
    background: #555;
}
ul {
    list-style: none;
    padding: 0;
}
li {
    background: #e4e4e4;
    margin: 5px;
    padding: 10px;
    border-radius: 3px;
}
.error {
    color: red;
    text-align: center;
}
.message {
    color: green;
    text-align: center;
}
```

### element_selector.js
```javascript
document.addEventListener('DOMContentLoaded', function() {
    var previewContainer = document.getElementById('preview-container');
    if (previewContainer) {
        previewContainer.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var el = e.target;
            // Build a basic CSS selector: tag#id.class1.class2
            var selector = el.tagName.toLowerCase();
            if (el.id) {
                selector += '#' + el.id;
            }
            if (el.className) {
                var classes = el.className.trim().split(/\s+/);
                classes.forEach(function(cls) {
                    selector += '.' + cls;
                });
            }
            // Optional: highlight the selected element
            el.style.outline = "2px solid red";
            // Populate the selector in the form
            var selectorInput = document.getElementById('selector');
            if (selectorInput) {
                selectorInput.value = selector;
            }
        });
    }
});
```

## Project Structure
```
web_scraper/
├── app.py              # Main application file
├── requirements.txt    # Project dependencies
├── usage.log          # Application logs
├── instance/          # Instance-specific files
├── static/            # Static files (CSS, JS, etc.)
├── templates/         # HTML templates
└── __pycache__/      # Python cache files

### 1. User Authentication
- User registration and login system
- Password hashing for security
- Session management
### 2. Web Scraping
- URL-based scraping using BeautifulSoup4
- CSS selector support
- Error handling and logging
### 3. Data Export
- Multiple format support (CSV, JSON, XLSX)
- Pandas integration for Excel export
- File download functionality
### 4. Database Models
- User management
- Scheduled jobs tracking
- Scraping results storage
### 5. Logging
- Activity tracking
- Error logging
- User action monitoring