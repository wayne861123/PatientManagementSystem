# Doctor's Clinic Management System

A Flask-based patient management system for tracking patient information, medical history, medication records, and doctor assignments.

## Features

### Patient Management
- **Patient Registration** - Register new patients with personal info, doctor assignment, and disease diagnosis
- **Patient Search & Filter** - Find patients by doctor, disease type, or keyword search (name, medical record number, ID number)
- **Patient Profile** - View complete patient history including demographics, medications, and examinations

### Dashboard & Reminders
- **Home Dashboard** (`/`) - Overview of all doctors with color-coded reminders:
  - Red alerts: Follow-up within 1 day OR biological drug dose depleted
  - Yellow alerts: Follow-up within 3 days OR biological drug dose ≤ 1
  - Only shows active patients (not "discharged")

### Medication Management
- **Traditional Medicine Records** - Track follow-up dates with configurable intervals
- **Biological Agent Records** - Track injection doses, application types (first/continue), and remaining doses
- **Additional Medications** - Support for supplementary medicines

### Examination Tracking
- **Examination Management** - Configurable examination items with follow-up intervals
- **Examination Records** - Log and track patient examination results over time
- **Examination History** - View all past examination records for a patient

### Clinical Tools
- **PASI Score Calculator** (`/pasi`) - Psoriasis Area and Severity Index assessment tool
- **Injection Frequency Calculator** (`/injection-frequency`) - Calculate injection schedules

### Data Management
- **Management Pages** - CRUD operations for doctors, diseases, examinations, and medicines
- **Audit Log System** - Records all database changes with timestamp, operator, and IP address
- **Data Rollback** - Revert any incorrect changes via CLI tools

## Pages & Routes

| Page | Route | Description |
|------|-------|-------------|
| **Home** | `/` | Dashboard showing all doctors with follow-up and dose reminders |
| **All Patients** | `/all-patients` | Filterable patient list by doctor, disease, or keyword |
| **Doctor Detail** | `/doctor/<id>` | View doctor's assigned diseases and patient counts |
| **Doctor's Patients** | `/doctor/<id>/disease/<id>` | List patients for a specific doctor-disease combination |
| **Patient Detail** | `/patient/<id>` | Full patient profile with medication & examination history |
| **Add Patient** | `/add_patient` | Register new patient with doctor and disease assignment |
| **Examination History** | `/history/examination/<id>` | All examination records for a patient |
| **Medicine History** | `/history/medicine/<id>` | Timeline of all medication records (traditional & biological) |
| **PASI Score** | `/pasi` | Calculator for Psoriasis Area and Severity Index |
| **Injection Frequency** | `/injection-frequency` | Tool to calculate injection schedules |
| **Manage Doctors** | `/management/doctors` | Add/edit/delete doctor records |
| **Manage Diseases** | `/management/diseases` | Add/edit/delete disease types |
| **Manage Examinations** | `/management/examinations` | Add/edit/delete examination items |
| **Manage Medicines** | `/management/medicines` | Add/edit/delete traditional & biological medicines |

## Setup

```bash
# Install dependencies
pip install flask

# Initialize database (automatic on first run)
python app.py

# Access the application
# Open browser: http://localhost:5000
```

## CLI Tools

The system includes a command-line tool for managing audit logs and data rollback:

```bash
# Query audit logs
python cli.py logs --table patients --limit 20
python cli.py logs --action INSERT --limit 50

# View log details
python cli.py log 123

# Preview rollback SQL (dry-run)
python cli.py revert 123 --dry-run

# Execute data rollback
python cli.py revert 123 --execute

# Interactive mode
python cli.py interactive
```

### Interactive Mode Commands
- `log <id>` - View log details
- `revert <id>` - Generate and optionally execute rollback SQL
- `tables` - List all database tables
- `exit` - Exit interactive mode

## Database Tables

- `patients` - Patient demographics and assignments
- `doctors` - Doctor records
- `diseases` - Disease types
- `traditional_medicines` - Traditional medication catalog
- `traditional_medicine_record` - Traditional medication logs
- `biological_medicines` - Biological agent catalog
- `biological_medicine_record` - Biological agent injection logs
- `examinations` - Examination item definitions
- `examination_record` - Patient examination results
- `pasi_records` - PASI score history
- `additional_medicines` - Supplementary medications
- `audit_log` - System audit trail

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML5/CSS3/JavaScript (Jinja2 templates)
- **Logging**: File-based audit logs with rotation

## Project Structure

```
wen2/
├── app.py              # Flask application and routes
├── database.py         # Database initialization and utilities
├── cli.py              # Command-line audit tools
├── patients.db         # SQLite database (auto-created)
├── logs/               # Application logs
├── static/
│   ├── style.css       # Stylesheets
│   └── script.js       # Client-side JavaScript
└── templates/
    ├── base.html       # Base template
    ├── home.html      # Dashboard
    ├── all_patients.html
    ├── patient_detail.html
    ├── add_patient.html
    ├── doctor.html
    ├── doctor_disease_patients.html
    ├── examination_history.html
    ├── history.html
    ├── management.html
    ├── pasi_score.html
    ├── injection_frequency.html
    └── new_medication.html