# In-Car Conversational AI

An intelligent conversational assistant designed for vehicle interiors. The application allows drivers and passengers to control simulated vehicle functions using natural-language text commands and voice commands.

The system combines a React frontend, a FastAPI backend, an AI command-processing module and a SQLite database for persistent users, profiles and vehicle sessions.

## Main Features

- Natural-language vehicle control
- Voice command support
- Temperature control for the driver and passenger
- Driver and passenger seat heating
- Fan speed control
- Volume control
- Media playback control
- Ambient lighting control
- Driver and passenger roles
- Persistent user accounts
- User profiles and personal preferences
- Active vehicle sessions
- Profile association with session participants
- AI command interpretation
- Whisper-based audio transcription
- Safety validation for vehicle commands
- Real-time vehicle state updates
- Cockpit-style dashboard
- Responsive user interface
- Weather and current time display
- Scrollable AI conversation
- Loading and error states

## System Architecture

```text
User
 │
 ├── Text command
 │
 └── Voice command
        │
        ▼
React Frontend
        │
        ├── POST /assistant/message
        └── POST /speech/transcribe
                    │
                    ▼
FastAPI Backend
        │
        ├── AI Engine
        ├── Whisper Transcription
        ├── Safety Validation
        ├── Vehicle Service
        ├── User Service
        ├── Profile Service
        └── Session Service
                    │
                    ▼
SQLite Database
```

## Technologies

### Frontend

- React
- TypeScript
- Vite
- HTML
- CSS
- Fetch API
- MediaRecorder API
- Browser localStorage

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn
- SQLite
- Pytest
- Whisper
- OpenAI API

### Development Tools

- Git
- GitLab
- VS Code
- Swagger/OpenAPI
- Postman
- npm
- Python virtual environment

## Project Structure

```text
team1_placeholder/
│
├── frontend/
│   ├── public/
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── AccountMenu.tsx
│   │   │   ├── AmbientLighting.tsx
│   │   │   ├── AssistantPanel.tsx
│   │   │   ├── Cockpit.tsx
│   │   │   ├── FanIndicator.tsx
│   │   │   ├── Layout.tsx
│   │   │   ├── MediaPanel.tsx
│   │   │   ├── PreferencesPanel.tsx
│   │   │   ├── SeatHeatingIndicator.tsx
│   │   │   └── VehicleStatus.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAnimatedNumber.ts
│   │   │   └── useSpeechRecognition.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── profileStorage.ts
│   │   │
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.css
│   │   ├── main.tsx
│   │   └── types.ts
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── engine.py
│   │   │   ├── fallback.py
│   │   │   ├── prompts.py
│   │   │   ├── safety.py
│   │   │   ├── schemas.py
│   │   │   ├── tools.py
│   │   │   └── transcription.py
│   │   │
│   │   ├── db/
│   │   │   ├── connection.py
│   │   │   └── init_db.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── profile_repository.py
│   │   │   ├── session_repository.py
│   │   │   └── user_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── ai_response.py
│   │   │   ├── profile.py
│   │   │   ├── session.py
│   │   │   └── user.py
│   │   │
│   │   ├── services/
│   │   │   ├── profile_service.py
│   │   │   ├── session_service.py
│   │   │   └── user_service.py
│   │   │
│   │   ├── vehicle/
│   │   │   ├── constants.py
│   │   │   ├── service.py
│   │   │   └── state.py
│   │   │
│   │   └── main.py
│   │
│   ├── data/
│   │   └── app.sqlite3
│   │
│   └── tests/
│       ├── test_ai_engine.py
│       ├── test_db_infrastructure.py
│       ├── test_profile_service.py
│       ├── test_safety.py
│       ├── test_session_service.py
│       └── test_vehicle_service.py
│
├── docs/
├── specs/
└── README.md
```

## Frontend

The frontend provides the user interface of the application.

### Main Components

#### Layout

Responsible for:

- Sidebar navigation
- Application header
- Current time
- Weather information
- Active user profile
- Main content area

#### Cockpit

Displays the simulated vehicle dashboard, including:

- Driver temperature
- Passenger temperature
- Seat heating
- Fan speed
- Volume
- Media status
- Air conditioning status
- Ambient lighting
- User preferences

#### AssistantPanel

Provides the conversational interface, including:

- User messages
- Assistant responses
- Text input
- Voice input
- Quick commands
- Loading state
- Error messages
- Scrollable conversation history

#### AccountMenu

Manages the active user and role selection.

It includes:

- Current user display
- Driver and passenger roles
- Login interface
- Sign up interface
- Edit Preferences option
- Logout functionality

#### PreferencesPanel

Allows users to configure personal preferences for the current role.

The available preferences include:

- Driver or passenger temperature
- Driver or passenger seat heating
- Fan speed
- Volume
- Ambient lighting

The preferences can be saved and applied to the current vehicle session.

## Backend

The backend is implemented using FastAPI and contains the main application logic.

### AI Module

The AI module:

- Receives natural-language messages
- Identifies the requested vehicle action
- Extracts action parameters
- Generates a conversational response
- Checks whether the action is allowed
- Returns structured vehicle actions

### Vehicle Service

The vehicle service manages the simulated vehicle state.

It controls:

- Temperature
- Seat heating
- Fan speed
- Volume
- Media playback
- Ambient lighting
- Air conditioning

The service validates action parameters before updating the state.

### Safety Module

The safety module rejects unsupported or dangerous actions.

Examples of rejected actions include:

- Accelerating
- Braking
- Overtaking
- Other unsupported driving operations

Rejected commands do not modify the vehicle state.

### User Service

The user service manages:

- User creation
- Unique `user_id` generation
- Email validation
- Password hashing
- User retrieval
- Login validation

Passwords are stored as secure hashes and are never returned by the API.

### Profile Service

The profile service manages:

- Creating profiles
- Listing user profiles
- Updating profiles
- Validating profile ownership
- Driver and passenger preferences
- Ambient lighting preferences

### Session Service

The session service manages:

- Creating active vehicle sessions
- Adding participants
- Assigning driver and passenger roles
- Associating profiles with participants
- Allowing only one driver per session
- Closing sessions

## Voice Command Flow

```text
User presses the microphone button
        ↓
Frontend records audio using MediaRecorder
        ↓
Audio is sent to /speech/transcribe
        ↓
Whisper converts audio into text
        ↓
The text is sent to /assistant/message
        ↓
The AI interprets the command
        ↓
The backend validates and executes the action
        ↓
The updated vehicle state is returned
        ↓
The result is displayed in the chat and cockpit
```

The existing speech transcription endpoint is:

```http
POST /speech/transcribe
```

## Text Command Flow

```text
User enters a text command
        ↓
Frontend sends the message to the backend
        ↓
AI identifies the requested action
        ↓
Safety validation is performed
        ↓
Vehicle state is updated
        ↓
Frontend displays the response
```

Example commands:

```text
Set the temperature to 24 degrees
Turn on the driver's seat heating
Increase the volume
Set the ambient light to purple
```

The application also supports Romanian commands generated from preference selections:

```text
Setează temperatura șoferului la 22 de grade
Setează lumina ambientală pe mov
Dă muzica mai tare
```

## API Endpoints

### General

```http
GET /health
```

Checks whether the backend is running.

### Vehicle

```http
GET /vehicle/state
POST /vehicle/reset
```

Reads or resets the simulated vehicle state.

### Assistant

```http
POST /assistant/message
```

Processes text or voice-transcribed commands.

Example request:

```json
{
  "message": "Set the temperature to 24 degrees",
  "speaker": "driver",
  "input_type": "text"
}
```

The `speaker` can be:

```text
driver
passenger
```

The `input_type` can be:

```text
text
voice
```

### Speech

```http
POST /speech/transcribe
```

Receives an audio file and returns the transcribed text.

### Users

```http
POST /users
GET /users/{user_id}
POST /auth/login
```

These endpoints support user creation, user retrieval and login.

### Profiles

```http
POST /profiles
GET /profiles
GET /profiles/{profile_id}
PUT /profiles/{profile_id}
```

These endpoints manage user-specific vehicle preferences.

### Sessions

```http
POST /sessions
GET /sessions/{session_id}
POST /sessions/{session_id}/participants
POST /sessions/{session_id}/profile
POST /sessions/{session_id}/close
```

These endpoints manage the current vehicle session and its participants.

## Database

The backend uses SQLite for persistent storage.

The database stores:

- Users
- Hashed passwords
- User profiles
- Vehicle preferences
- Vehicle sessions
- Session participants
- Driver and passenger roles
- Voice enrollment fields prepared for future speaker recognition

The database is initialized automatically when the backend starts.

Sensitive information such as passwords, API keys and audio files must not be committed to Git.

## Weather and Time

The frontend displays the current time and updates it every second.

Weather data is loaded from the Open-Meteo API using the coordinates of Cluj-Napoca:

```text
Latitude: 46.7712
Longitude: 23.6236
```

The browser geolocation API is not required.

## Installation and Setup

### Requirements

Install the following tools:

- Python 3.11 or newer
- Node.js and npm
- Git
- An OpenAI API key
- A supported browser with microphone access

### Backend Setup

Open a terminal in the backend directory:

```powershell
cd C:\Endava\EndevLocal\team1_placeholder\backend
```

Create the virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure the required environment variables according to the backend configuration.

Start the backend:

```powershell
python -m uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

To leave the virtual environment:

```powershell
deactivate
```

### Frontend Setup

Open a second terminal:

```powershell
cd C:\Endava\EndevLocal\team1_placeholder\frontend
```

Install the dependencies:

```powershell
npm.cmd install
```

Start the development server:

```powershell
npm.cmd run dev
```

The frontend will run at:

```text
http://localhost:5173
```

### Frontend Build

To check the TypeScript code and create a production build:

```powershell
npm.cmd run build
```

### Backend Tests

From the backend directory, with the virtual environment activated:

```powershell
pytest
```

## Development Workflow

The project uses Git and GitLab branches.

Recommended workflow:

```text
Update dev branch
        ↓
Create a feature branch
        ↓
Write or update the specification
        ↓
Implement the feature
        ↓
Run tests and build checks
        ↓
Push the branch
        ↓
Create a merge request
```

Example:

```powershell
git switch dev
git pull
git switch -c 001-feature-name
git push -u origin HEAD
```

## Development Status

The project currently includes:

- React and TypeScript frontend
- FastAPI backend
- AI command interpretation
- Whisper voice transcription
- Simulated vehicle service
- Safety validation
- SQLite persistence
- User accounts
- Login endpoint
- User profiles
- Vehicle preferences
- Active vehicle sessions
- Driver and passenger roles
- Cockpit dashboard
- Media controls
- Ambient lighting
- Text commands
- Voice commands
- Responsive styling
- Automated backend tests

## Future Improvements

Possible future improvements include:

- Full JWT authentication
- Persistent frontend authentication state
- Speaker recognition
- Voice enrollment
- Voice embeddings
- Automatic speaker identification
- Automatic role detection
- Applying profiles directly to the vehicle state
- More advanced microphone animations
- Improved mobile and tablet layouts
- Integration with real vehicle data
- Additional safety and permission rules
- More extensive frontend test coverage

## License

This project was developed as part of an academic and internship project focused on conversational AI for automotive applications.
