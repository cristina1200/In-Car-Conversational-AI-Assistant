import { useEffect, useState } from "react";

import type {
  ChangeEvent,
  FormEvent,
} from "react";

import type { CSSProperties } from "react";

import Layout, {
  type ActiveView,
} from "./components/Layout";

import Cockpit from "./components/Cockpit";
import PreferencesPanel from "./components/PreferencesPanel";

import AssistantPanel from "./components/AssistantPanel";

import type { ChatMessage } from "./components/AssistantPanel";

import {
  createProfile,
  addSessionParticipant,
  ensureSessionForUser,
  getSession,
  getProfiles,
  listVoiceEnrolledUsers,
  removeSessionParticipant,
  getVehicleState,
  identifyVoiceSpeaker,
  sendAssistantMessage,
  updateSessionParticipantRole,
  updateProfile,
} from "./services/api";

import type {
  AssistantRequest,
  AssistantResponse,
  ConversationMessage,
  InputType,
  SessionRole,
  Speaker,
  UserPreferences,
  UserProfile,
  VehicleAction,
  VehicleSession,
  VehicleState,
  VoiceEnrolledUser,
} from "./types";

import { useSpeechRecognition } from "./hooks/useSpeechRecognition";

import {
  AMBIENT_COLOR_LABELS_RO,
  DEFAULT_AMBIENT_LIGHT,
  DEFAULT_AC_ENABLED,
  DEFAULT_CURRENT_SONG,
  DEFAULT_DRIVER_SEAT_HEATING,
  DEFAULT_DRIVER_TEMPERATURE,
  DEFAULT_FAN_SPEED,
  DEFAULT_IS_MUTED,
  DEFAULT_IS_PLAYING,
  DEFAULT_PASSENGER_SEAT_HEATING,
  DEFAULT_PASSENGER_TEMPERATURE,
  DEFAULT_VOLUME,
} from "./constants";

import {
  clearAuthPersistence,
  loadLocalSession,
  loadLocalUser,
  clearLocalUser,
  saveLocalSession,
  saveLocalUser,
} from "./services/profileStorage";

import "./App.css";

const initialState: VehicleState = {
  temperature: {
    driver: DEFAULT_DRIVER_TEMPERATURE,
    passenger: DEFAULT_PASSENGER_TEMPERATURE,
  },

  seat_heating: {
    driver: DEFAULT_DRIVER_SEAT_HEATING,
    passenger: DEFAULT_PASSENGER_SEAT_HEATING,
  },

  fan_speed: DEFAULT_FAN_SPEED,
  volume: DEFAULT_VOLUME,
  current_song: DEFAULT_CURRENT_SONG,
  is_playing: DEFAULT_IS_PLAYING,
  is_muted: DEFAULT_IS_MUTED,
  ambient_light: DEFAULT_AMBIENT_LIGHT,
  ac_enabled: DEFAULT_AC_ENABLED,
};

const accentColors: Record<string, string> = {
  blue: "#69c5ff",
  green: "#62e6b0",
  purple: "#c18cff",
  red: "#ff7b7b",
  yellow: "#ffd66b",
  white: "#dff6ff",
};

const defaultPreferences: UserPreferences = {
  driver_temperature: initialState.temperature.driver,
  passenger_temperature: initialState.temperature.driver,
  driver_seat_heating: initialState.seat_heating.driver,
  passenger_seat_heating: initialState.seat_heating.passenger,
  fan_speed: initialState.fan_speed,
  volume: initialState.volume,
  ambient_light: DEFAULT_AMBIENT_LIGHT,
};

const initialAssistantMessage: ChatMessage = {
  id: 1,
  role: "assistant",
  text: "Hello! I am ready to help you.",
  allowed: true,
};

type AuthModeRequest = "login" | "signup";

function App() {
  const [vehicleState, setVehicleState] =
    useState<VehicleState>(initialState);

  const [currentUser, setCurrentUser] =
    useState<UserProfile | null>(() =>
      loadLocalUser()
    );

  const [session, setSession] =
  useState<VehicleSession>(() => loadLocalSession());

  const [voiceEnrolledUsers, setVoiceEnrolledUsers] =
    useState<VoiceEnrolledUser[]>([]);

  const [selectedParticipantId, setSelectedParticipantId] =
    useState("");

  const [preferences, setPreferences] =
  useState<UserPreferences>(
    defaultPreferences
  );

  const [currentProfileId, setCurrentProfileId] =
    useState<string | null>(null);

  const [isPreferencesOpen, setIsPreferencesOpen] =
    useState(false);

  const [authModeRequest, setAuthModeRequest] =
    useState<AuthModeRequest | null>(null);

  const currentParticipant =
    session.participants.find(
      (participant) =>
        participant.user_id ===
        currentUser?.user_id
    );

  const speaker: Speaker | undefined =
    currentParticipant?.role;

  const activeRole: SessionRole =
    currentParticipant?.role ?? "driver";

  const [activeView, setActiveView] =
    useState<ActiveView>("cabin");

  const [messages, setMessages] = useState<
    ChatMessage[]
  >([initialAssistantMessage]);

  const [actionHistory, setActionHistory] =
    useState<VehicleAction[]>([]);

  const [chatSessionId, setChatSessionId] =
    useState<string | null>(null);

  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] =
    useState(false);
  const [isConnected, setIsConnected] =
    useState(false);
  const [error, setError] = useState("");

  async function handleUserChange(
    user: UserProfile | null
  ) {
    setCurrentUser(user);

    if (user) {
      saveLocalUser(user);
      if (session.session_id) {
        try {
          const backendSession = await getSession(session.session_id);
          setSession(backendSession);
          saveLocalSession(backendSession);
        } catch {
          setError("Sesiunea curentă nu mai este disponibilă în backend.");
        }
      }
      return;
    } else {
      clearLocalUser();
    }

    clearAuthPersistence();
    setCurrentProfileId(null);
    setPreferences(defaultPreferences);
  }

  useEffect(() => {
    void listVoiceEnrolledUsers()
      .then(setVoiceEnrolledUsers)
      .catch(() => setVoiceEnrolledUsers([]));
  }, []);

  async function handleRoleChange(
    role: SessionRole
  ) {
    if (!currentUser) {
      return;
    }

    try {
      setError("");
      let backendSession: VehicleSession | null = null;

      if (session.session_id) {
        try {
          backendSession = await getSession(session.session_id);
        } catch {
          backendSession = null;
        }
      }

      if (!backendSession) {
        backendSession = await ensureSessionForUser(
          currentUser.user_id,
          role
        );
      } else {
        const participant = backendSession.participants.find(
          (candidate) => candidate.user_id === currentUser.user_id
        );
        if (participant) {
          await updateSessionParticipantRole(
            backendSession.session_id,
            currentUser.user_id,
            role
          );
        } else {
          await addSessionParticipant(
            backendSession.session_id,
            { user_id: currentUser.user_id, role }
          );
        }
        backendSession = await getSession(backendSession.session_id);
      }

      setSession(backendSession);
      saveLocalSession(backendSession);
    } catch (roleError) {
      setError(
        roleError instanceof Error
          ? roleError.message
          : "Nu am putut actualiza rolul în sesiunea curentă."
      );
    }
  }

  async function handleAddParticipant(
    userId: string,
    role: SessionRole
  ) {
    try {
      setError("");
      let activeSession: VehicleSession;
      try {
        activeSession = session.session_id
          ? await getSession(session.session_id)
          : await ensureSessionForUser(userId, role);
      } catch {
        activeSession = await ensureSessionForUser(userId, role);
      }

      if (!activeSession.participants.some((participant) => participant.user_id === userId)) {
        await addSessionParticipant(activeSession.session_id, { user_id: userId, role });
      } else {
        await updateSessionParticipantRole(activeSession.session_id, userId, role);
      }

      const refreshedSession = await getSession(activeSession.session_id);
      setSession(refreshedSession);
      saveLocalSession(refreshedSession);
    } catch (participantError) {
      setError(
        participantError instanceof Error
          ? participantError.message
          : "Nu am putut actualiza participanții sesiunii."
      );
    }
  }

  async function handleRemoveParticipant(userId: string) {
    if (!session.session_id) {
      return;
    }

    try {
      await removeSessionParticipant(session.session_id, userId);
      const refreshedSession = await getSession(session.session_id);
      setSession(refreshedSession);
      saveLocalSession(refreshedSession);
    } catch (participantError) {
      setError(
        participantError instanceof Error
          ? participantError.message
          : "Nu am putut elimina participantul din sesiune."
      );
    }
  }

  async function handleParticipantRoleChange(
    userId: string,
    role: SessionRole
  ) {
    if (!session.session_id) {
      return;
    }

    try {
      await updateSessionParticipantRole(session.session_id, userId, role);
      const refreshedSession = await getSession(session.session_id);
      setSession(refreshedSession);
      saveLocalSession(refreshedSession);
    } catch (participantError) {
      setError(
        participantError instanceof Error
          ? participantError.message
          : "Nu am putut schimba rolul participantului."
      );
    }
  }

  function handleAuthRequestHandled() {
    setAuthModeRequest(null);
  }

  async function handleSavePreferences(
    nextPreferences: UserPreferences
  ) {
    if (!currentUser) {
      setError(
        "You need to be logged in to save preferences."
      );
      return;
    }

    try {
      setError("");

      const sharedTemperature =
        activeRole === "driver"
          ? nextPreferences.driver_temperature ??
            nextPreferences.passenger_temperature ??
            initialState.temperature.driver
          : nextPreferences.passenger_temperature ??
            nextPreferences.driver_temperature ??
            initialState.temperature.driver;

      const sharedSeatHeating =
        activeRole === "driver"
          ? nextPreferences.driver_seat_heating ??
            nextPreferences.passenger_seat_heating ??
            initialState.seat_heating.driver
          : nextPreferences.passenger_seat_heating ??
            nextPreferences.driver_seat_heating ??
            initialState.seat_heating.driver;

      const normalizedPreferences: UserPreferences = {
        ...nextPreferences,
        driver_temperature: sharedTemperature,
        passenger_temperature: sharedTemperature,
        driver_seat_heating: sharedSeatHeating,
        passenger_seat_heating: sharedSeatHeating,
      };

      if (currentProfileId) {
        const updatedProfile =
          await updateProfile(
            currentProfileId,
            currentUser.user_id,
            {
              driver_temperature:
                normalizedPreferences.driver_temperature,

              passenger_temperature:
                normalizedPreferences.passenger_temperature,

              driver_seat_heating:
                normalizedPreferences.driver_seat_heating,

              passenger_seat_heating:
                normalizedPreferences.passenger_seat_heating,

              fan_speed:
                normalizedPreferences.fan_speed,

              volume:
                normalizedPreferences.volume,

              ambient_light:
                normalizedPreferences.ambient_light,

              is_default: true,
            }
          );

        const updatedPreferences: UserPreferences = {
          ...normalizedPreferences,
          profile_id:
            updatedProfile.profile_id,
          user_id:
            updatedProfile.user_id,
          profile_name:
            updatedProfile.profile_name,
          is_default:
            updatedProfile.is_default,
        };

        setPreferences(
          updatedPreferences
        );

        const updatedUser: UserProfile = {
          ...currentUser,
          preferences:
            updatedPreferences,
        };

        setCurrentUser(updatedUser);
        saveLocalUser(updatedUser);

      } else {
        const createdProfile =
          await createProfile({
            user_id:
              currentUser.user_id,

            profile_name:
              "Default",

            driver_temperature:
              normalizedPreferences.driver_temperature ??
              initialState.temperature.driver,

            passenger_temperature:
              normalizedPreferences.passenger_temperature ??
              initialState.temperature.passenger,

            driver_seat_heating:
              normalizedPreferences.driver_seat_heating ??
              initialState.seat_heating.driver,

            passenger_seat_heating:
              normalizedPreferences.passenger_seat_heating ??
              initialState.seat_heating.passenger,

            fan_speed:
              normalizedPreferences.fan_speed ??
              initialState.fan_speed,

            volume:
              normalizedPreferences.volume ??
              initialState.volume,

            ambient_light:
              normalizedPreferences.ambient_light ??
              DEFAULT_AMBIENT_LIGHT,

            is_default: true,
          });

        setCurrentProfileId(
          createdProfile.profile_id
        );

        const createdPreferences: UserPreferences = {
          ...normalizedPreferences,

          profile_id:
            createdProfile.profile_id,

          user_id:
            createdProfile.user_id,

          profile_name:
            createdProfile.profile_name,

          is_default:
            createdProfile.is_default,
        };

        setPreferences(
          createdPreferences
        );

        const updatedUser: UserProfile = {
          ...currentUser,
          preferences:
            createdPreferences,
        };

        setCurrentUser(updatedUser);
        saveLocalUser(updatedUser);
      }

      setIsPreferencesOpen(false);

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not save preferences."
      );
    }
  }

  function handleApplyPreferences() {
    const sharedTemperature =
      preferences.driver_temperature ??
      preferences.passenger_temperature ??
      initialState.temperature.driver;
    const sharedSeatHeating =
      preferences.driver_seat_heating ??
      preferences.passenger_seat_heating ??
      initialState.seat_heating.driver;

    const sharedCommands = [
      `Setează temperatura la ${sharedTemperature} grade`,
      `încălzirea în scaune la nivelul ${sharedSeatHeating}`,
    ];

    const command = [
      ...sharedCommands,
      `ventilatorul la nivelul ${preferences.fan_speed}`,
      `volumul la ${preferences.volume}`,
      `lumina ambientală pe ${AMBIENT_COLOR_LABELS_RO[preferences.ambient_light ?? DEFAULT_AMBIENT_LIGHT] ?? AMBIENT_COLOR_LABELS_RO[DEFAULT_AMBIENT_LIGHT]}`,
    ].join(", ");

    setMessage(`${command}.`);
    setIsPreferencesOpen(false);
  }

  useEffect(() => {
    async function loadUserPreferences() {
      if (!currentUser) {
        setCurrentProfileId(null);
        setPreferences(defaultPreferences);
        return;
      }

      try {
        const profiles =
          await getProfiles(
            currentUser.user_id
          );

        if (profiles.length === 0) {
          setCurrentProfileId(null);
          setPreferences(
            defaultPreferences
          );

          return;
        }

        const selectedProfile =
          profiles.find(
            (profile) =>
              profile.is_default
          ) ?? profiles[0];

        setCurrentProfileId(
          selectedProfile.profile_id
        );

        const loadedPreferences: UserPreferences = {
          profile_id:
            selectedProfile.profile_id,

          user_id:
            selectedProfile.user_id,

          profile_name:
            selectedProfile.profile_name,

          is_default:
            selectedProfile.is_default,

          driver_temperature:
            selectedProfile.driver_temperature,

          passenger_temperature:
            selectedProfile.driver_temperature,

          driver_seat_heating:
            selectedProfile.driver_seat_heating,

          passenger_seat_heating:
            selectedProfile.driver_seat_heating,

          fan_speed:
            selectedProfile.fan_speed,

          volume:
            selectedProfile.volume,

          ambient_light:
            selectedProfile.ambient_light as UserPreferences["ambient_light"],
        };

        setPreferences(
          loadedPreferences
        );

      } catch (error) {
        console.error(
          "Could not load preferences:",
          error
        );
      }
    }

    void loadUserPreferences();
  }, [currentUser]);

  useEffect(() => {
    async function ensureSession() {
      if (!currentUser) {
        return;
      }

      // Session membership is created explicitly from the role selector.
      if (false) {
        try {
          const nextSession = await ensureSessionForUser(currentUser?.user_id ?? "", "driver");
          setSession(nextSession);
          saveLocalSession(nextSession);
        } catch {
          setError("Nu am putut crea o sesiune activă pentru utilizator.");
        }
      }
    }

    void ensureSession();
  }, [currentUser]);

  useEffect(() => {
    async function loadVehicleState() {
      try {
        const state =
          await getVehicleState();

        setVehicleState(state);
        setIsConnected(true);
      } catch {
        setIsConnected(false);
      }
    }

    void loadVehicleState();
  }, []);

  async function submitMessage(
    text: string,
    inputType: InputType,
    audioBlob?: Blob
  ) {
    const trimmedMessage = text.trim();

    if (
      !trimmedMessage ||
      isLoading
    ) {
      return;
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: Date.now(),
        role: "user",
        text: trimmedMessage,
      },
    ]);

    setMessage("");
    setIsLoading(true);
    setError("");

    const history: ConversationMessage[] = messages
      .filter((chatMessage) => chatMessage.text.trim())
      .map((chatMessage) => ({
        role: chatMessage.role,
        content: chatMessage.text,
      }));

    try {
      let requestPayload: AssistantRequest = {
        message: trimmedMessage,
        speaker,
        input_type: inputType,
        session_id: chatSessionId,
        history,
        action_history: actionHistory,
      };

      if (inputType === "voice") {
        if (!currentUser) {
          throw new Error(
            "Trebuie să fii autentificat pentru o comandă vocală."
          );
        }

        let activeSession = session;

        if (
          !activeSession.session_id ||
          !activeSession.participants.some(
            (participant) =>
              participant.user_id ===
              currentUser.user_id
          )
        ) {
          throw new Error(
            "Alege Driver sau Passenger în sesiunea curentă înainte de comanda vocală."
          );
        }

        if (!audioBlob) {
          throw new Error(
            "Înregistrarea audio lipsește pentru identificarea vocii."
          );
        }

        const identification = await identifyVoiceSpeaker(
          audioBlob,
          activeSession.session_id
        );

        if (
          !identification.matched ||
          !identification.user_id
        ) {
          const comfortCommandPattern =
            /(temperatur|volum|ventilator|scaun|lumina|ambient|melodie|muzic|music|ac|climat|climate|fan)/i;

          if (comfortCommandPattern.test(trimmedMessage)) {
            requestPayload = {
              message: trimmedMessage,
              speaker: undefined,
              input_type: inputType,
              session_id: chatSessionId,
              history,
              action_history: actionHistory,
            };

            setError(
              "Nu am reușit să identific vorbitorul, așa că am aplicat comanda pe ambele părți."
            );
          } else {
            throw new Error(
              "Nu am putut identifica utilizatorul din voce. Repetă comanda."
            );
          }
        } else {
          const matchedSpeakerRole = identification.role;

          requestPayload = {
            message: trimmedMessage,
            speaker: matchedSpeakerRole ?? undefined,
            input_type: inputType,
            user_id: identification.user_id,
            session_id: activeSession.session_id,
            history,
            action_history: actionHistory,
          };

          if (identification.user_name) {
            setError(
              `Vorbitor identificat: ${identification.user_name} (${identification.confidence.toFixed(2)}).`
            );
          }

          if (!matchedSpeakerRole) {
            setError(
              "Vorbitorul a fost identificat, dar nu are rol în sesiunea curentă; aplic fallback-ul fără speaker."
            );
          }
        }
      }

      if (
        inputType !== "voice" &&
        currentUser
      ) {
        requestPayload = {
          ...requestPayload,
          user_id: currentUser.user_id,
        };
      }

      if (
        inputType !== "voice" &&
        session.session_id
      ) {
        requestPayload = {
          ...requestPayload,
          session_id: session.session_id,
        };
      }

      const response: AssistantResponse =
        await sendAssistantMessage(
          requestPayload
        );

      setVehicleState(response.state);
      setIsConnected(true);
      setChatSessionId(response.session_id);

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: response.reply,
          allowed: response.allowed,
        },
      ]);
      setActionHistory((currentActions) => [
        ...currentActions,
        ...response.actions,
      ]);
    } catch (error) {
      setIsConnected(false);

      const detail =
        error instanceof Error
          ? error.message
          : "Backend-ul nu este disponibil momentan.";

      setError(detail);

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: detail,
          allowed: false,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleMessageChange(
    event: ChangeEvent<HTMLInputElement>
  ) {
    setMessage(event.target.value);
  }

  function handleQuickCommand(
    command: string
  ) {
    setMessage(command);
  }

  function handlePanelCommand(
    command: string
  ) {
    setMessage(command);
  }

  function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    void submitMessage(
      message,
      "text"
    );
  }

  const {
    startListening,
    stopListening,
    isListening,
    speechError,
  } = useSpeechRecognition(
    async (transcript, audioBlob) => {
      await submitMessage(
        transcript,
        "voice",
        audioBlob
      );
    }
  );

  const accentColor =
    accentColors[
      vehicleState.ambient_light
    ] ?? accentColors.blue;

  return (
    <div
      className="app-theme"
      style={
        {
          "--accent-color": accentColor,
        } as CSSProperties
      }
    >
      <Layout
        currentUser={currentUser}
        sessionRole={
          currentParticipant?.role ?? null
        }
        onUserChange={handleUserChange}
        onRoleChange={handleRoleChange}
        onEditPreferences={() => setIsPreferencesOpen(true)}
        authModeRequest={authModeRequest}
        onAuthRequestHandled={handleAuthRequestHandled}
        activeView={activeView}
        onViewChange={setActiveView}
      >
        <section className="session-participants-panel" aria-label="Participanții sesiunii curente">
          <div className="session-participants-heading">
            <span>Participanții sesiunii curente</span>
            <span>{session.participants.length}</span>
          </div>
          {session.participants.length === 0 && (
            <p className="session-participants-empty">Nu există participanți în sesiune.</p>
          )}
          <ul>
            {session.participants.map((participant) => {
              const enrolledUser = voiceEnrolledUsers.find(
                (user) => user.user_id === participant.user_id
              );
              return (
                <li key={participant.user_id}>
                  <span>{enrolledUser?.name ?? `User ${participant.user_id.slice(0, 8)}`}</span>
                  <span className="session-participant-actions">
                    <button type="button" onClick={() => void handleParticipantRoleChange(participant.user_id, "driver")} disabled={participant.role === "driver"}>Driver</button>
                    <button type="button" onClick={() => void handleParticipantRoleChange(participant.user_id, "passenger")} disabled={participant.role === "passenger"}>Passenger</button>
                    <button type="button" onClick={() => void handleRemoveParticipant(participant.user_id)}>Remove</button>
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="session-participant-add">
            <select value={selectedParticipantId} onChange={(event) => setSelectedParticipantId(event.target.value)}>
              <option value="">Select enrolled user</option>
              {voiceEnrolledUsers
                .filter((user) => !session.participants.some((participant) => participant.user_id === user.user_id))
                .map((user) => <option key={user.user_id} value={user.user_id}>{user.name}</option>)}
            </select>
            <button type="button" disabled={!selectedParticipantId} onClick={() => { void handleAddParticipant(selectedParticipantId, "passenger"); setSelectedParticipantId(""); }}>Add passenger</button>
            <button type="button" disabled={!selectedParticipantId || session.participants.some((participant) => participant.role === "driver")} onClick={() => { void handleAddParticipant(selectedParticipantId, "driver"); setSelectedParticipantId(""); }}>Add driver</button>
          </div>
        </section>
        <section className="app-dashboard">
          <div className="app-cockpit-column">
            <Cockpit
              vehicleState={vehicleState}
              isConnected={isConnected}
              activeView={activeView}
              onCommand={handlePanelCommand}
              preferences={preferences}
              currentUser={currentUser}
              onOpenAuth={(mode) =>
                setAuthModeRequest(mode)
              }
              sessionRole={activeRole}
              currentUserName={currentUser?.name ?? null}
              onApplyPreferences={handleApplyPreferences}
            />
          </div>

          <AssistantPanel
            messages={messages}
            message={message}
            isLoading={isLoading}
            error={error || speechError}
            isListening={isListening}
            onStartListening={
              startListening
            }
            onStopListening={
              stopListening
            }
            onMessageChange={
              handleMessageChange
            }
            onSubmit={handleSubmit}
            onQuickCommand={
              handleQuickCommand
            }
          />
        </section>

        <PreferencesPanel
          key={isPreferencesOpen ? "preferences-open" : "preferences-closed"}
          vehicleState={vehicleState}
          preferences={preferences}
          sessionRole={activeRole}
          isOpen={isPreferencesOpen}
          onApply={handleSavePreferences}
          onClose={() => setIsPreferencesOpen(false)}
        />
      </Layout>
    </div>
  );
}

export default App;
