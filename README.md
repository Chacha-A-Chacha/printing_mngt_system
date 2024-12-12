# Printing Management System

## Overview
A comprehensive Flask-based application for managing large format printing and outsourced production workflows.

## Features
- In-House Printing Tracking
- Outsourced Production Management
- Inventory Control
- Client and Supplier Management
- Reporting and Analytics

## Setup and Installation

### Prerequisites
- Python 3.9+
- pip
- virtualenv (recommended)

### Installation Steps
1. Clone the repository
```bash
git clone https://github.com/yourusername/printing-management-system.git
cd printing-management-system
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
# Create a .env file
touch .env
# Add configuration variables
```

5. Initialize the database
```bash
flask db upgrade
```

6. Run the application
```bash
python run.py
```

## Development

### Running Tests
```bash
pytest tests/
```

### Migrations
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

## Deployment
- Recommended: Use Gunicorn for production
- Set `FLASK_ENV=production`
- Configure a production database (PostgreSQL recommended)

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
[Specify your license]