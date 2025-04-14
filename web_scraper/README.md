# Web Scraper Project Documentation

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
```

## Main Components

### app.py
The main application file containing:
- Flask web application setup
- Database models (User, ScheduledJob, ScrapingResult)
- Web scraping functionality
- Authentication routes
- API endpoints for scraping and scheduling
- Export functionality (CSV, JSON, XLSX)

### requirements.txt
Project dependencies:
- Flask (3.0.0) - Web framework
- Requests (2.31.0) - HTTP library
- BeautifulSoup4 (4.12.2) - HTML parsing
- Pandas (2.1.4) - Data manipulation
- Selenium (4.15.0) - Web automation
- XlsxWriter (3.1.9) - Excel file creation
- APScheduler (3.10.4) - Task scheduling
- Flask-SQLAlchemy (3.1.1) - Database ORM
- Werkzeug (3.1.3) - WSGI utilities

## Features
1. User Authentication
   - Registration
   - Login/Logout
   - User-specific scraping jobs

2. Web Scraping
   - URL-based scraping
   - CSS selector support
   - Preview functionality
   - Multiple export formats (CSV, JSON, XLSX)

3. Scheduled Jobs
   - Create recurring scraping tasks
   - Manage scheduled jobs
   - View scraping results

4. Data Export
   - CSV export
   - JSON export
   - Excel (XLSX) export

## Logging
- Application logs are stored in `usage.log`
- Tracks user activities and scraping operations
- Error logging for debugging

## Database Models
1. User
   - Username
   - Email
   - Password (hashed)
   - Creation timestamp

2. ScheduledJob
   - Job ID
   - URL
   - CSS Selector
   - Interval
   - Next run time
   - User association

3. ScrapingResult
   - Job association
   - Scraped data
   - Timestamp 

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