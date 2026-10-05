# In-Car Conversational AI – Frontend

A modern cockpit-style frontend for an in-car conversational AI assistant. The interface is designed to help drivers and passengers interact with vehicle functions through a clear, hands-free-oriented visual experience.

## Technologies

* React
* TypeScript
* Vite
* CSS
* HTML

## Implemented Features

* Dark navy-blue cockpit interface
* Virtual cockpit dashboard
* Sidebar navigation
* Cabin, Navigation, Media, and Vehicle sections
* Application header with:

  * Weather information
  * Current time
  * Active user profile
* Driver and Passenger profile selection
* Expandable account menu
* Add new account option
* Login modal prototype
* Sign up modal prototype
* Central cockpit dashboard
* Temperature controls for the driver and passenger
* Animated temperature dial
* Fan speed indicator
* Driver and passenger seat heating levels
* Three-level seat heating indicators
* Volume progress bar
* Current media information
* Ambient light indicator
* AI assistant chat interface
* User and assistant message bubbles
* Quick command buttons
* Loading state while processing a command
* Error message display
* Scrollable chat area
* Responsive layout for smaller screens

## Frontend Structure

```text
src/
├── components/
│   ├── Layout.tsx
│   ├── Layout.css
│   ├── Cockpit.tsx
│   ├── Cockpit.css
│   ├── AssistantPanel.tsx
│   ├── AssistantPanel.css
│   ├── AccountMenu.tsx
│   └── AccountMenu.css
│
├── services/
│   └── api.ts
│
├── App.tsx
├── App.css
├── index.css
├── types.ts
└── main.tsx
```

## Component Responsibilities

### Layout

The `Layout` component defines the general structure of the application.

It contains:

* Sidebar navigation
* Application header
* Weather display
* Current time
* Active user profile
* Main content area

### Cockpit

The `Cockpit` component represents the virtual vehicle dashboard.

It contains:

* Driver temperature control
* Passenger temperature control
* Rotating temperature dials
* Fan speed display
* Seat heating indicators
* Volume control
* Ambient light information
* Media information
* Dashboard status cards

### AssistantPanel

The `AssistantPanel` component represents the conversational interface.

It contains:

* Assistant header
* User messages
* Assistant responses
* Message bubbles
* Quick command buttons
* Text input
* Microphone button placeholder
* Send button
* Loading indicator
* Scrollable conversation area
* Error messages

### AccountMenu

The `AccountMenu` component manages the user profile interface.

It contains:

* Active Driver profile
* Passenger profile
* Expandable account bar
* Add new account button
* Login interface
* Sign up interface
* Email and password fields
* Close button for the authentication modal

The authentication interface is currently a visual prototype. Its purpose is to establish the final user experience before the real authentication functionality is implemented.

## Dashboard Design

The interface uses a dark navy-blue visual theme inspired by modern vehicle infotainment systems.

The dashboard includes:

* Dark blue backgrounds
* Light blue highlights
* Cyan and red temperature indicators
* Glowing control elements
* Rounded panels
* Clear visual hierarchy
* High contrast text
* Smooth transitions and animations

The central cockpit area is designed to resemble a vehicle dashboard. The temperature controls use circular dials to visually represent climate values.

## Temperature Controls

The driver and passenger temperatures are displayed separately.

Each temperature control includes:

* User label
* Current temperature
* Circular dial
* Rotating indicator
* Climate label
* Blue and red visual temperature scale

The dial changes its position when the temperature value changes. Lower temperatures are represented using blue tones, while higher temperatures use warmer colors.

## Seat Heating Controls

The seat heating interface uses three visual levels:

```text
Level 0: ▯ ▯ ▯
Level 1: ▮ ▯ ▯
Level 2: ▮ ▮ ▯
Level 3: ▮ ▮ ▮
```

The levels are also represented through colors:

* Level 0: grey
* Level 1: light blue
* Level 2: orange
* Level 3: red

This ensures that the user can understand the selected level even without relying only on color.

## Assistant Chat

The assistant chat is displayed in a dedicated panel on the right side of the application.

The chat interface includes:

* Separate user and assistant messages
* Different colors for each message type
* Rounded message bubbles
* Assistant avatar
* User avatar
* Quick command suggestions
* Scrollable conversation history
* Text input field
* Microphone button placeholder
* Send button

The chat area has its own scrollbar so the entire page does not need to be scrolled when the conversation becomes longer.

## Account Interface

The account bar is displayed in the top-right corner.

When collapsed, it displays the current profile:

```text
● Driver ⌄
```

When expanded, it displays:

```text
Select profile

● Driver       ✓
● Passenger

＋ Add new account
```

Selecting `Add new account` opens the authentication modal with Login and Sign up options.

## Responsive Design

The frontend adapts to different screen sizes.

On smaller screens:

* The sidebar is hidden
* The main content uses the full available width
* The cockpit and assistant panel are displayed vertically
* Status cards use multiple rows
* The chat remains scrollable
* The account menu remains accessible

## Running the Frontend

Open a terminal in the frontend directory:

```powershell
cd C:\Endava\EndevLocal\team1_placeholder\frontend
```

Install the project dependencies:

```powershell
npm.cmd install
```

Start the development server:

```powershell
npm.cmd run dev
```

The application will be available at:

```text
http://localhost:5173
```

## Development Status

Implemented frontend functionality:

* React and TypeScript project setup
* Component-based frontend structure
* Cockpit dashboard interface
* Temperature visualization
* Seat heating visualization
* Volume visualization
* Fan speed visualization
* Media status visualization
* Ambient light visualization
* AI chat interface
* Quick command interface
* Expandable account menu
* Login and Sign up modal prototype
* Responsive styling
* Scrollable chat panel
* Navy-blue cockpit theme

## Future Frontend Improvements

* Replace the temporary navigation visualization with the final cockpit design
* Improve positioning of the dashboard controls
* Add a functional microphone interaction
* Add listening-state animations
* Add more detailed seat heating animations
* Add smoother temperature dial transitions
* Improve mobile and tablet layouts
* Add visual feedback for rejected commands
* Add user profile personalization
