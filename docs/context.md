# Web Scraper

A powerful and user-friendly web scraping tool that enables data extraction from any website - no coding knowledge required.

## Overview

Web Scraper provides an intuitive interface for selecting elements, scheduling scraping tasks, and exporting data in various formats. Built with modern technologies, it offers both simplicity for beginners and advanced features for professionals.

## Key Features

### Visual Element Selection
- Point-and-click interface for selecting webpage elements
- Real-time preview of selected elements
- Visual feedback for selection validation

### Automated Scheduling
- Schedule scraping tasks at custom intervals
- Automated execution with email notifications
- Task management dashboard

### Flexible Data Export
- Multiple export formats supported:
  - CSV
  - JSON
  - Excel (XLSX)
  - Direct database integration
- Customizable data formatting

### Task Management
- Complete history of scraping tasks
- One-click task replication
- Result archiving and retrieval

### Security
- Secure user authentication
- Encrypted data storage
- Rate limiting and proxy support

## Technical Stack

| Component | Technologies |
|-----------|-------------|
| Frontend  | Flask / Django |
| Backend   | Python (BeautifulSoup, Scrapy) |
| Database  | PostgreSQL / SQLite |
| Scheduler | Celery |
| Export    | Pandas |

## Database Schema

### Tables

#### Users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

#### Scraping_Tasks
```sql
CREATE TABLE scraping_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    schedule_type VARCHAR(20), -- once, daily, weekly, monthly
    schedule_interval INTEGER,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Scraping_Rules
```sql
CREATE TABLE scraping_rules (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES scraping_tasks(id),
    selector_type VARCHAR(20), -- css, xpath
    selector_value TEXT,
    field_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Scraping_Results
```sql
CREATE TABLE scraping_results (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES scraping_tasks(id),
    data JSONB,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),
    error_message TEXT
);
```

#### Export_Jobs
```sql
CREATE TABLE export_jobs (
    id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES scraping_results(id),
    format VARCHAR(10), -- CSV, JSON, XLSX
    status VARCHAR(20),
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Project Structure
```
web_scraper/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   └── result.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scraper.py
│   │   ├── scheduler.py
│   │   └── exporter.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── validators.py
│   ├── web/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   └── utils/
│       ├── __init__.py
│       ├── security.py
│       └── helpers.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   └── tasks/
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   └── test_api.py
├── docs/
│   ├── context.md
│   ├── api.md
│   └── deployment.md
├── migrations/
├── requirements.txt
├── README.md
└── .env.example
```

## Getting Started

1. Clone the repository
2. Install dependencies
3. Configure environment variables
4. Launch the application

## Quick Start Guide

1. Launch the application
2. Enter target website URL
3. Select elements using the visual tool
4. Configure export settings
5. Start scraping
6. Download results

## Roadmap

- [ ] REST API implementation
- [ ] Cloud-based distributed scraping
- [ ] Advanced analytics dashboard
- [ ] Custom scraping rules engine
- [ ] Browser extension integration

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


# Web Scraper: A Powerful and User-Friendly Web Scraping Tool

## Overview
The Web Scraper is a powerful yet easy-to-use tool that allows users to extract data from any website without requiring any coding knowledge. It provides a simple and modern interface where users can select elements to scrape, schedule scraping tasks, and export data in various formats like CSV.

## Features

### 1. **User-Friendly Interface**
- Intuitive UI designed for both regular and professional users.
- Simple drag-and-select functionality to choose elements for scraping.
- Modern design with smooth navigation.

### 2. **Website Input & Element Selection**
- Users can enter the URL of the website they want to scrape.
- Interactive element selection using a point-and-click method.
- Ability to preview selected elements before scraping.

### 3. **Scheduled Scraping**
- Users can schedule scraping tasks at specific intervals (e.g., daily, weekly, custom times).
- Automated execution without manual intervention.
- Notifications upon task completion.

### 4. **Data Export Options**
- Export scraped data in multiple formats such as:
  - CSV
  - JSON
  - Excel (XLSX)
  - Database integration (optional)

### 5. **History Tracking**
- Keeps a record of previously scraped websites.
- Users can revisit and manage past scraping tasks.
- Option to re-run previous scraping tasks with updated data.

### 6. **Authentication & Secure Access**
- User authentication system for secure access.
- Login/logout functionality.
- Encryption for stored data.

## Tech Stack
- **Frontend:** Flask, Tkinter (for GUI), or Django (optional for web-based UI)
- **Backend:** Python (BeautifulSoup, Scrapy, Selenium)
- **Database:** SQLite / PostgreSQL / MySQL (for history tracking)
- **Scheduling:** Celery, APScheduler
- **Export Handling:** Pandas for data transformation & export

## Installation & Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/your-repo/web-scraper.git
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the application:
   ```sh
   python app.py
   ```

## Usage Guide
1. **Enter the website URL** in the input field.
2. **Select elements** from the webpage using the point-and-click tool.
3. **Choose export format** (CSV, JSON, etc.).
4. **Set a schedule** (optional) for automatic scraping.
5. **Click "Start Scraping"** to begin data extraction.
6. **Download and view the extracted data.**

## Future Enhancements
- API integration for programmatic access.
- Cloud-based scraping for large-scale data extraction.
- Advanced data visualization and analytics.

---

This document serves as a comprehensive guide to the Web Scraper project, ensuring clarity for developers and contributors.

