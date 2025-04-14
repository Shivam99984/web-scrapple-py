import logging
import io, csv, json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash, jsonify
import requests
from bs4 import BeautifulSoup
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
from apscheduler.jobstores.base import JobLookupError

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure random key


# Configure logging for user activity
logging.basicConfig(filename='usage.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------------
# Database Models
# ---------------------

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

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# ---------------------
# APScheduler Setup
# ---------------------
scheduler = BackgroundScheduler()
scheduler.start()

# ---------------------
# Helper Functions
# ---------------------
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
        return db.session.get(User, session['user_id'])
    return None

# Add current_user to template context
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ---------------------
# Routes for Authentication
# ---------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another one.", 'error')
            return redirect(url_for('register'))
            
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash("Email address already registered. Please use a different email or try logging in.", 'error')
            return redirect(url_for('register'))
            
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! You can now log in.", 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", 'error')
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f"Welcome back, {username}! You have successfully logged in.", 'success')
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password. Please try again.", 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been successfully logged out. See you soon!", 'info')
    return redirect(url_for('index'))

@app.route('/download_result/<int:result_id>', methods=['GET'])
def download_result(result_id):
    # Retrieve the scraping result from the database
    result = ScrapingResult.query.get_or_404(result_id)
    
    # Get the export format from the query parameter, default to CSV
    export_format = request.args.get('format', 'csv').lower()
    data = json.loads(result.data)  # Assuming data is stored as a JSON list

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
            download_name=f"result_{result.id}.csv"
        )
    elif export_format == 'json':
        json_data = json.dumps(data)
        return send_file(
            io.BytesIO(json_data.encode()),
            mimetype="application/json",
            as_attachment=True,
            download_name=f"result_{result.id}.json"
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
            download_name=f"result_{result.id}.xlsx"
        )
    else:
        return "Unsupported format", 400

# ---------------------
# Main Application Routes
# ---------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            return redirect(url_for('preview', url=url))
        else:
            error = "Please provide a website URL."
    return render_template('index.html', error=error, user=current_user())

@app.route('/preview')
def preview():
    """Load the HTML content for preview so the user can select an element."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Please provide a website URL'}), 400
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an exception for 4XX and 5XX status codes
        html_content = response.text
        logging.info(f"Preview loaded for URL: {url}")
        return render_template('preview.html', url=url, html_content=html_content)
    except requests.exceptions.HTTPError as e:
        error_msg = f"Error loading preview for {url}: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f"Error loading preview for {url}: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 400

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    selector = request.form.get('selector')
    if not url or not selector:
        flash("Please provide both URL and selector.", 'error')
        return redirect(url_for('index'))
    
    results = perform_scraping(url, selector)
    if not results:
        flash("No data found with the provided selector. Please try a different selector.", 'warning')
    else:
        flash(f"Successfully scraped {len(results)} items from the website!", 'success')
    return render_template('results.html', url=url, selector=selector, results=results)

@app.route('/export', methods=['POST'])
def export():
    """Export scraped data in the chosen format: CSV, JSON, or XLSX."""
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
    else:
        return "Unsupported export format", 400

# ---------------------
# Scheduled Job Routes
# ---------------------
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if not current_user():
        flash("Please log in to schedule a task.", 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        url = request.form.get('url')
        selector = request.form.get('selector')
        scheduled_time_str = request.form.get('scheduled_time')
        try:
            if not scheduled_time_str:
                raise Exception("Scheduled time is required.")
            scheduled_datetime = datetime.strptime(scheduled_time_str, "%Y-%m-%dT%H:%M")
            job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            new_job = ScheduledJob(
                job_id=job_id,
                url=url,
                selector=selector,
                interval=0,
                next_run=scheduled_datetime,
                user_id=current_user().id
            )
            db.session.add(new_job)
            db.session.commit()
            
            def scheduled_job(job_db_id=new_job.id, url=url, selector=selector, job_id=job_id):
                with app.app_context():
                    try:
                        results = perform_scraping(url, selector)
                        if results:
                            result_record = ScrapingResult(
                                scheduled_job_id=job_db_id,
                                data=json.dumps(results)
                            )
                            db.session.add(result_record)
                            db.session.commit()
                            logging.info(f"Scheduled job {job_id} executed successfully.")
                        else:
                            logging.error(f"Scheduled job {job_id} failed: No results returned")
                    except Exception as e:
                        logging.error(f"Scheduled job {job_id} failed: {str(e)}")
            
            job = scheduler.add_job(scheduled_job, 'date', run_date=scheduled_datetime, id=job_id)
            new_job.next_run = job.next_run_time
            db.session.commit()
            
            flash(f"Job scheduled successfully! It will run at {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}", 'success')
            return redirect(url_for('schedule'))
        except Exception as e:
            flash(f"Error scheduling job: {str(e)}", 'error')
            return redirect(url_for('schedule'))
    
    jobs = ScheduledJob.query.filter_by(user_id=current_user().id).all()
    for job in jobs:
        job.status = 'pending'
        if job.next_run and job.next_run < datetime.now():
            if job.results:
                job.status = 'completed'
            else:
                job.status = 'failed'
    return render_template('schedule.html', jobs=jobs, now=datetime.now())

@app.route('/delete_job/<int:job_db_id>', methods=['POST'])
def delete_job(job_db_id):
    if not current_user():
        flash("Please log in to remove a task.", 'warning')
        return redirect(url_for('login'))
    
    job = ScheduledJob.query.get_or_404(job_db_id)
    if job.user_id != current_user().id:
        flash("You are not authorized to delete this job.", 'error')
        return redirect(url_for('schedule'))
    
    try:
        # Try to remove from scheduler if it exists
        try:
            scheduler.remove_job(job.job_id)
        except JobLookupError:
            # Job doesn't exist in scheduler, but that's okay
            pass
        
        # Delete associated results
        ScrapingResult.query.filter_by(scheduled_job_id=job.id).delete()
        
        # Delete the job from database
        db.session.delete(job)
        db.session.commit()
        
        flash("Job successfully deleted!", 'success')
    except Exception as e:
        flash(f"Error deleting job: {str(e)}", 'error')
        db.session.rollback()
    
    return redirect(url_for('schedule'))

@app.route('/routes')
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        output.append(str(rule))
    return "<br>".join(output)

@app.route('/logs')
def view_logs():
    search_query = request.args.get('search', '').lower()
    category_filter = request.args.getlist('category')  # Changed to getlist for multiple categories
    
    log_entries = []
    try:
        with open('usage.log', 'r') as f:
            for line in f:
                # Match format: "2025-04-12 18:57:34,970 INFO: Message"
                match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+(\w+):\s*(.*)', line)
                if match:
                    timestamp, category, message = match.groups()
                    
                    # Skip static file requests and other unwanted logs
                    if any(x in message for x in [
                        '/static/', 
                        'GET /static/', 
                        'HTTP/1.1" 304', 
                        'HTTP/1.1" 404', 
                        'GET /logs HTTP/1.1 200', 
                        'GET /logs?search=&category= HTTP/1.1 200',
                        'GET /favicon.ico',
                        'GET / HTTP/1.1',
                        'GET /index HTTP/1.1',
                        'GET /schedule HTTP/1.1',
                        'GET /preview HTTP/1.1',
                        'GET /scrape HTTP/1.1',
                        'GET /export HTTP/1.1',
                        'GET /static/css/',
                        'GET /static/js/',
                        'GET /static/img/',
                        'GET /static/fonts/',
                        'GET /static/vendor/',
                        'GET /register HTTP/',
                        'GET /login HTTP/',
                        'GET /logs HTTP/'
                    ]):
                        continue
                    
                    # Define category colors for badges with more specific categories
                    category_colors = {
                        'ERROR': 'danger',           # Red - for critical errors
                        'WARNING': 'warning',        # Yellow - for warnings
                        'INFO': 'info',              # Blue - for general information
                        'DEBUG': 'secondary',        # Gray - for debug messages
                        'SUCCESS': 'success',        # Green - for successful operations
                        'SCRAPING': 'primary',       # Blue - for scraping operations
                        'SCHEDULED': 'info',         # Light blue - for scheduled jobs
                        'EXPORT': 'success',         # Green - for export operations
                        'AUTH': 'primary',           # Blue - for authentication events
                        'DATABASE': 'info',          # Light blue - for database operations
                        'SYSTEM': 'secondary'        # Gray - for system operations
                    }
                    
                    # Format the message to be more readable
                    formatted_message = message.strip()
                    
                    # Categorize messages based on content
                    if 'Preview loaded for URL:' in message:
                        category = 'SUCCESS'
                    elif 'Scraped URL:' in message or 'Scraping' in message:
                        category = 'SCRAPING'
                    elif 'Scheduled job' in message or 'Job scheduled' in message:
                        category = 'SCHEDULED'
                    elif any(x in message.lower() for x in [
                        'export', 'download', 'download_result', 'download_job_results',
                        'GET /download_job_results/', 'GET /download_result/',
                        'sending file', 'file downloaded', 'exporting data'
                    ]):
                        category = 'EXPORT'
                    elif any(x in message.lower() for x in [
                        'user', 'login', 'register', 'session', 'auth', 'authenticated',
                        'GET /login HTTP/1.1', 'POST /login HTTP/1.1'
                    ]):
                        category = 'AUTH'
                    elif any(x in message.lower() for x in [
                        'database', 'sql', 'db.session', 'query', 'commit', 'rollback',
                        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER',
                        'GET /register HTTP/1.1', 'POST /register HTTP/1.1'
                    ]):
                        category = 'DATABASE'
                    elif any(x in message.lower() for x in [
                        'system', 'server', 'backgroundscheduler', 'scheduler',
                        'job store', 'job execution'
                    ]):
                        category = 'SYSTEM'
                    
                    if 'GET' in formatted_message or 'POST' in formatted_message:
                        # Format HTTP requests to be more readable
                        parts = formatted_message.split('"')
                        if len(parts) >= 2:
                            method_path = parts[1]
                            status = parts[2].split()[0] if len(parts) > 2 else ''
                            formatted_message = f"{method_path} {status}"
                    
                    entry = {
                        'timestamp': timestamp,
                        'category': category.upper(),
                        'category_color': category_colors.get(category.upper(), 'secondary'),
                        'message': formatted_message
                    }
                    
                    # Apply filters
                    if category_filter and category.upper() not in [c.upper() for c in category_filter]:
                        continue
                        
                    if search_query and search_query not in message.lower():
                        continue
                        
                    log_entries.append(entry)
                    
    except FileNotFoundError:
        log_entries = []
    
    # Sort entries by timestamp (newest first)
    log_entries.reverse()
    
    return render_template('log_viewer.html', log_entries=log_entries)

@app.route('/download_job_results/<int:job_id>', methods=['GET'])
def download_job_results(job_id):
    if not current_user():
        flash("Please log in to download results.")
        return redirect(url_for('login'))
    
    job = ScheduledJob.query.get_or_404(job_id)
    if job.user_id != current_user().id:
        flash("You are not authorized to download these results.")
        return redirect(url_for('schedule'))
    
    # Get the export format from the query parameter, default to CSV
    export_format = request.args.get('format', 'csv').lower()
    
    # Get all results for this job
    results = ScrapingResult.query.filter_by(scheduled_job_id=job.id).all()
    if not results:
        flash("No results found for this job.")
        return redirect(url_for('schedule'))
    
    # Combine all results into a single list
    all_data = []
    for result in results:
        try:
            data = json.loads(result.data)
            all_data.extend(data)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON data for result {result.id}")
            continue
    
    # Create a descriptive filename
    domain = job.url.split('//')[-1].split('/')[0].replace('.', '_')
    selector = job.selector.replace('.', '_').replace('#', '_')
    timestamp = job.next_run.strftime('%Y%m%d_%H%M')
    filename = f"scrape_{domain}_{selector}_{timestamp}"
    
    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Scraped Data'])
        for item in all_data:
            writer.writerow([item])
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{filename}.csv"
        )
    elif export_format == 'json':
        json_data = json.dumps(all_data)
        return send_file(
            io.BytesIO(json_data.encode()),
            mimetype="application/json",
            as_attachment=True,
            download_name=f"{filename}.json"
        )
    elif export_format == 'xlsx':
        df = pd.DataFrame(all_data, columns=["Scraped Data"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{filename}.xlsx"
        )
    else:
        return "Unsupported format", 400

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

if __name__ == '__main__':
    app.run(debug=True)
