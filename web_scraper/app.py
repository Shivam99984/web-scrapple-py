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
        return User.query.get(session['user_id'])
    return None

# ---------------------
# Routes for Authentication
# ---------------------
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
    """Load the HTML content for preview so the user can click and select an element."""
    url = request.args.get('url')
    if not url:
        return redirect(url_for('index'))
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text  # In production, sanitize this HTML.
        logging.info(f"Preview loaded for URL: {url}")
        return render_template('preview.html', url=url, html_content=html_content, user=current_user())
    except Exception as e:
        logging.error(f"Error loading preview for {url}: {e}")
        return f"Error loading preview: {e}"

@app.route('/scrape', methods=['POST'])
def scrape():
    """Scrape the target URL using the selected CSS selector."""
    url = request.form.get('url')
    selector = request.form.get('selector')
    if not url or not selector:
        return redirect(url_for('index'))
    results = perform_scraping(url, selector)
    # Optionally, save results for logged-in user and associated scheduled job (if applicable)
    return render_template('results.html', url=url, selector=selector, results=results, user=current_user())

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
        flash("Please log in to schedule a task.")
        return redirect(url_for('login'))
    message = None
    if request.method == 'POST':
        url = request.form.get('url')
        selector = request.form.get('selector')
        scheduled_time_str = request.form.get('scheduled_time')  # new datetime input from user
        try:
            if not scheduled_time_str:
                raise Exception("Scheduled time is required.")
            # Convert the HTML5 datetime-local value to a Python datetime object.
            scheduled_datetime = datetime.strptime(scheduled_time_str, "%Y-%m-%dT%H:%M")
            job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Step 1: Create the ScheduledJob record first.
            new_job = ScheduledJob(
                job_id=job_id,
                url=url,
                selector=selector,
                interval=0,  # Not used for a one-time job; adjust as needed.
                next_run=scheduled_datetime,  # Store the scheduled run time.
                user_id=current_user().id
            )
            db.session.add(new_job)
            db.session.commit()  # new_job.id is now available.
            
            # Step 2: Define the scheduled job function using a closure capturing new_job.id.
            def scheduled_job(job_db_id=new_job.id, url=url, selector=selector, job_id=job_id):
                with app.app_context():
                    results = perform_scraping(url, selector)
                    # Save the scraping results in the database.
                    result_record = ScrapingResult(
                        scheduled_job_id=job_db_id,
                        data=json.dumps(results)
                    )
                    db.session.add(result_record)
                    db.session.commit()
                    logging.info(f"Scheduled job {job_id} executed. Results saved.")
            
            # Step 3: Schedule the job with APScheduler using a date trigger.
            job = scheduler.add_job(scheduled_job, 'date', run_date=scheduled_datetime, id=job_id)
            
            # Update new_job with the next run time from APScheduler.
            new_job.next_run = job.next_run_time
            db.session.commit()
            
            message = f"Job scheduled successfully with ID: {job_id} to run at {scheduled_datetime}"
            logging.info(message)
        except Exception as e:
            message = f"Error scheduling job: {e}"
            logging.error(message)
    # Retrieve scheduled jobs for the current user.
    jobs = ScheduledJob.query.filter_by(user_id=current_user().id).all()
    return render_template('schedule.html', message=message, jobs=jobs, user=current_user())


@app.route('/routes')
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        output.append(str(rule))
    return "<br>".join(output)

@app.route('/delete_job/<int:job_db_id>', methods=['POST'])
def delete_job(job_db_id):
    if not current_user():
        flash("Please log in to remove a task.")
        return redirect(url_for('login'))
    job = ScheduledJob.query.get_or_404(job_db_id)
    # Ensure the job belongs to the current user
    if job.user_id != current_user().id:
        flash("You are not authorized to delete this job.")
        return redirect(url_for('schedule'))
    try:
        # Remove from APScheduler
        scheduler.remove_job(job.job_id)
    except Exception as e:
        logging.error(f"Error removing job {job.job_id} from scheduler: {e}")
    # Remove from database
    db.session.delete(job)
    db.session.commit()
    flash("Scheduled job removed successfully.")
    return redirect(url_for('schedule'))

@app.route('/logs')
def logs():
    """Display the usage logs."""
    try:
        with open('usage.log', 'r') as f:
            log_data = f.read()
        return f"<pre>{log_data}</pre>"
    except Exception as e:
        return f"Error reading logs: {e}"

if __name__ == '__main__':
    app.run(debug=True)
