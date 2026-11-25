# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teachers can sign students up for activities
- Teachers can unregister students from activities
- Students can view activity participants without logging in

## Teacher access

Teacher credentials are stored locally in `teachers.json`. Create a teacher account
from the `src` directory:

```
python manage_teachers.py
```

The script prompts for a username and password and stores a salted password hash.
Do not commit `teachers.json`; it is ignored by Git. A schema example is available
in `teachers.json.example`. Teachers sign in from the account menu in the top-right
corner of the activities page.

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                     | Sign in as a teacher and establish a session                        |
| GET    | `/auth/session`                                                   | Check the current teacher session                                   |
| POST   | `/auth/logout`                                                    | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only activity signup                                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only activity unregister                                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data and teacher sessions are stored in memory, so activity changes reset
and teachers must sign in again when the server restarts.
