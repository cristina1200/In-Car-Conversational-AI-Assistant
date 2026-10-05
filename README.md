# In-Car Conversational AI Assistant

A modern cockpit-style web application that allows drivers and passengers to interact with vehicle functions through natural language and voice commands.

The assistant can control climate settings, seat heating, fan speed, media, volume and ambient lighting. The application combines a React frontend with a FastAPI backend and an AI processing module.

## Features

- Cockpit-style vehicle dashboard
- Driver and passenger temperature display
- Animated temperature dials
- Driver and passenger seat heating levels
- Fan speed indicator
- Volume control and progress visualization
- Media status and current song display
- Ambient lighting controls
- Romanian natural-language commands
- Text-based AI assistant
- Voice command recording using the browser microphone
- Audio transcription using Whisper
- Scrollable assistant chat
- Automatic scroll to the newest message
- Quick command buttons
- Loading and error states
- Driver and passenger role selection
- User preferences management
- Driver-specific and passenger-specific preferences
- Apply Preferences functionality
- Login and Sign up interface
- User profile menu
- Current user and session information
- Current time display
- Cluj-Napoca weather display
- Responsive layout for smaller screens
- Safety validation for unsupported vehicle commands

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
- SQLite
- Pydantic
- Uvicorn
- Pytest
- Whisper for audio transcription
- OpenAI API for conversational command processing

## Application Architecture

The project is divided into three main parts:

```text
Frontend → Backend API → AI and Vehicle Services
```

The frontend is responsible for displaying the cockpit interface, collecting user input and sending requests to the backend.

The backend processes messages, validates vehicle actions, updates the simulated vehicle state and returns the result to the frontend.

The AI module interprets natural-language commands and converts them into structured vehicle actions.

## Frontend Structure

```text
frontend/
├── public/
│   └── dashboard assets
│
├── src/
│   ├── components/
│   │   ├── AccountMenu.tsx
│   │   ├── AccountMenu.css
│   │   ├── AmbientLighting.tsx
│   │   ├── AmbientLighting.css
│   │   ├── AssistantPanel.tsx
│   │   ├── AssistantPanel.css
│   │   ├── Cockpit.tsx
│   │   ├── Cockpit.css
│   │   ├── FanIndicator.tsx
│   │   ├── Layout.tsx
│   │   ├── Layout.css
│   │   ├── MediaPanel.tsx
│   │   ├── MediaPanel.css
│   │   ├── PreferencesPanel.tsx
│   │   ├── PreferencesPanel.css
│   │   ├── SeatHeatingIndicator.tsx
│   │   ├── VehicleStatus.tsx
│   │   └── VehicleStatus.css
│   │
│   ├── hooks/
│   │   ├── useAnimatedNumber.ts
│   │   └── useSpeechRecognition.ts
│   │
│   ├── services/
│   │   ├── api.ts
│   │   └── profileStorage.ts
│   │
│   ├── App.tsx
│   ├── App.css
│   ├── index.css
│   ├── main.tsx
│   └── types.ts
│
├── package.json
└── vite.config.ts
```

## Main Components

### Layout

The `Layout` component defines the general application structure.

It contains:

- Sidebar navigation
- Application header
- Current weather
- Current time
- Active user profile
- Main content area

### Cockpit

The `Cockpit` component displays the main vehicle dashboard.

It contains:

- Driver temperature
- Passenger temperature
- Animated temperature dials
- Seat heating status
- Fan speed
- Volume
- Media status
- Air conditioning status
- Ambient lighting status
- User preference summary

### AssistantPanel

The `AssistantPanel` component contains the conversational interface.

It provides:

- User and assistant messages
- Message bubbles
- Quick commands
- Text input
- Microphone recording
- Send button
- Loading state
- Error messages
- Scrollable conversation history

### AccountMenu

The `AccountMenu` component manages the current user profile.

It provides:

- Active user display
- Driver and passenger role selection
- Expandable profile menu
- Login interface
- Sign up interface
- Edit Preferences option
- Logout functionality

### PreferencesPanel

The `PreferencesPanel` allows the current user to configure personal vehicle preferences.

Depending on the selected role, the user can configure:

- Driver or passenger temperature
- Driver or passenger seat heating
- Fan speed
- Volume
- Ambient lighting

The selected preferences can be saved and applied to the current vehicle session.

### AmbientLighting

The `AmbientLighting` component allows the user to select the interior lighting color.

Available colors include:

- Blue
- Red
- Green
- White
- Purple
- Yellow

The interface displays the colors in English, while the generated chat commands use Romanian color names such as `albastru`, `roșu`, `alb` and `mov`.

## Voice Command Flow

The voice interaction follows this flow:

```text
User presses the microphone button
        ↓
Browser records audio using MediaRecorder
        ↓
Audio file is sent to /speech/transcribe
        ↓
Whisper converts audio into text
        ↓
The text is sent to /assistant/message
        ↓
The AI interprets the command
        ↓
The vehicle state is updated
        ↓
The response is displayed in the chat
```

Voice recording is implemented on the frontend, while audio transcription is handled by the backend.

## Text Command Flow

For a text command, the flow is:

```text
User enters a message
        ↓
Frontend sends the message to the backend
        ↓
AI interprets the request
        ↓
Backend validates the action
        ↓
Vehicle state is updated
        ↓
Frontend displays the response
```

Example commands:

```text
Set the temperature to 24 degrees
Turn on the seat heating
Increase the volume
Set the ambient light to purple
```

The frontend also supports Romanian commands generated from preference selections, such as:

```text
Setează temperatura șoferului la 22 de grade
Setează lumina ambientală pe mov
Dă muzica mai tare
```

## Backend API

The frontend communicates with the following backend endpoints:

```text
GET  /health
GET  /vehicle/state
POST /vehicle/reset
POST /assistant/message
POST /speech/transcribe
POST /users
POST /auth/login
GET  /users/{user_id}
POST /profiles
GET  /profiles
PUT  /profiles/{profile_id}
POST /sessions
GET  /sessions/{session_id}
```

### Assistant message request

```json
{
  "message": "Set the temperature to 24 degrees",
  "speaker": "driver",
  "input_type": "text"
}
```

### Assistant response

```json
{
  "reply": "I set the driver's temperature to 24°C.",
  "actions": [],
  "allowed": true,
  "state": {}
}
```

The `speaker` field can be:

```text
driver
passenger
```

The `input_type` field can be:

```text
text
voice
```

## User Profiles and Preferences

Users can have a stable `user_id`, name, email and personal preferences.

The application supports:

- Driver and passenger roles
- Current vehicle session
- User-specific preferences
- Driver-specific temperature and seat heating
- Passenger-specific temperature and seat heating
- Fan speed preference
- Volume preference
- Ambient light preference

The frontend is prepared to communicate with the persistent user and profile endpoints provided by the backend.

## Safety

The backend validates the requested vehicle actions before changing the vehicle state.

Unsupported or dangerous commands are rejected and do not modify the simulated vehicle state.

The system is designed to prevent commands related to:

- Acceleration
- Braking
- Dangerous driving actions
- Unsupported vehicle operations

## Weather and Time

The application header displays the current time, updated every second.

Weather information is loaded from the Open-Meteo API using the coordinates of Cluj-Napoca:

```text
Latitude: 46.7712
Longitude: 23.6236
```

The browser geolocation API is not required.

## Running the Project

### Backend

Open a terminal in the backend directory:

```powershell
cd C:\Endava\EndevLocal\team1_placeholder\backend
```

Create the virtual environment if it does not already exist:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

To deactivate the virtual environment:

```powershell
deactivate
```

### Frontend

Open a second terminal in the frontend directory:

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

The frontend will be available at:

```text
http://localhost:5173
```

### Frontend production build

To verify the TypeScript code and create a production build:

```powershell
npm.cmd run build
```

## Development Workflow

The project uses Git and GitLab for version control.

Recommended workflow:

```text
Update dev branch
        ↓
Create a feature branch
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

- Component-based React frontend
- TypeScript type definitions
- Cockpit dashboard
- Vehicle state visualization
- AI chat interface
- Voice recording and transcription flow
- User profile interface
- Preference management
- Driver and passenger roles
- Session support
- Backend API integration
- Ambient lighting controls
- Weather and time display
- Responsive styling
- Loading and error states
- Safety validation

## Future Improvements

Possible future improvements include:

- Complete JWT authentication
- Persistent frontend authentication state
- Speaker recognition
- Voice enrollment
- Automatic speaker role identification
- Applying user profiles directly to the vehicle state
- More advanced microphone animations
- Improved mobile and tablet layouts
- Integration with real vehicle data
- Additional safety and permission rules
- Full automated frontend and backend test coverage

## License

This project was developed as part of an academic and internship project focused on conversational AI for automotive applications.
