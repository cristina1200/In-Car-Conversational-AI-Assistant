import {
  useEffect,
  useRef,
  useState,
} from "react";

import type { MouseEvent } from "react";

import type {
  SessionRole,
  UserProfile,
} from "../types";

import {
  clearAuthPersistence,
  saveLocalUser,
} from "../services/profileStorage";

import {
  createUser,
  enrollVoiceProfile,
  deleteUser,
  loginUser,
} from "../services/api";

import {
  DEFAULT_AMBIENT_LIGHT,
  DEFAULT_DRIVER_SEAT_HEATING,
  DEFAULT_DRIVER_TEMPERATURE,
  DEFAULT_FAN_SPEED,
  DEFAULT_PASSENGER_SEAT_HEATING,
  DEFAULT_PASSENGER_TEMPERATURE,
  DEFAULT_VOLUME,
} from "../constants";

import "./AccountMenu.css";

interface AccountMenuProps {
  currentUser: UserProfile | null;
  sessionRole: SessionRole | null;
  onUserChange: (
    user: UserProfile | null
  ) => void;
  onRoleChange: (
    role: SessionRole
  ) => void;
  onEditPreferences: () => void;
  authModeRequest: "login" | "signup" | null;
  onAuthRequestHandled: () => void;
}

type AuthMode = "login" | "signup";
type DeleteResult = "success" | "error" | null;

function AccountMenu({
  currentUser,
  sessionRole,
  onUserChange,
  onRoleChange,
  onEditPreferences,
  authModeRequest,
  onAuthRequestHandled,
}: AccountMenuProps) {
  const [isMenuOpen, setIsMenuOpen] =
    useState(false);

  const accountMenuRef =
    useRef<HTMLDivElement>(null);

  const [isModalOpen, setIsModalOpen] =
    useState(false);

  const authBackdropMouseDown =
    useRef(false);

  const [authMode, setAuthMode] =
    useState<AuthMode>("login");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] =
    useState("");

  const [authError, setAuthError] =
    useState("");

  const [isAuthLoading, setIsAuthLoading] =
    useState(false);

  const [isVoiceModalOpen, setIsVoiceModalOpen] =
    useState(false);

  const [voicePhraseIndex, setVoicePhraseIndex] =
    useState(0);

  const [voiceSamples, setVoiceSamples] =
    useState<Blob[]>([]);

  const [isVoiceRecording, setIsVoiceRecording] =
    useState(false);

  const [voiceError, setVoiceError] =
    useState("");

  const [voiceMessage, setVoiceMessage] =
    useState("");

  const voiceRecorderRef =
    useRef<MediaRecorder | null>(null);

  const voiceStreamRef =
    useRef<MediaStream | null>(null);

  const voiceChunksRef = useRef<Blob[]>([]);

  const voicePhrases = [
    "Setează temperatura șoferului la 22 de grade.",
    "Mărește volumul la 70 la sută.",
    "Pornește încălzirea scaunului pasagerului la nivelul 2.",
    "Schimbă lumina ambientală pe albastru.",
    "Reia următoarea melodie.",
  ];

  const [isDeleteLoading, setIsDeleteLoading] =
    useState(false);

  const [isDeleteModalOpen, setIsDeleteModalOpen] =
    useState(false);

  const [deleteResult, setDeleteResult] =
    useState<DeleteResult>(null);

  const [deleteError, setDeleteError] =
    useState("");

  useEffect(() => {
    if (!isMenuOpen) {
      return;
    }

    function handleOutsideMouseDown(
      event: globalThis.MouseEvent
    ) {
      const target = event.target;

      if (
        target instanceof Node &&
        !accountMenuRef.current?.contains(target)
      ) {
        setIsMenuOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleOutsideMouseDown
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideMouseDown
      );
    };
  }, [isMenuOpen]);

  useEffect(() => {
    if (!authModeRequest) {
      return;
    }

    setAuthMode(authModeRequest);
    setAuthError("");
    setIsModalOpen(true);
    setIsMenuOpen(false);
    onAuthRequestHandled();
  }, [authModeRequest]);

  function openModal(mode: AuthMode) {
    setAuthMode(mode);
    setAuthError("");
    setIsModalOpen(true);
    setIsMenuOpen(false);
  }

  function closeModal() {
    setIsModalOpen(false);
    setName("");
    setEmail("");
    setPassword("");
    setAuthError(""); 
  }

  function handleAuthBackdropMouseDown(
    event: MouseEvent<HTMLDivElement>
  ) {
    authBackdropMouseDown.current =
      event.target === event.currentTarget;
  }

  function handleAuthBackdropClick(
    event: MouseEvent<HTMLDivElement>
  ) {
    const shouldClose =
      authBackdropMouseDown.current &&
      event.target === event.currentTarget;

    authBackdropMouseDown.current = false;

    if (shouldClose) {
      closeModal();
    }
  }

  async function submitAuth() {
  if (!email.trim() || !password.trim()) {
    setAuthError(
      "Please enter your email and password."
    );
    return;
  }

  if (
    authMode === "signup" &&
    !name.trim()
  ) {
    setAuthError(
      "Please enter your name."
    );
    return;
  }

  setAuthError("");
  setIsAuthLoading(true);

  try {
    const userResponse =
      authMode === "signup"
        ? await createUser({
            name: name.trim(),
            email: email.trim(),
            password,
          })
        : await loginUser({
            email: email.trim(),
            password,
          });

    const user: UserProfile = {
      user_id: userResponse.user_id,
      name: userResponse.name,
      email: userResponse.email,
      voice_enrolled:
        userResponse.voice_enrolled,
      created_at:
        userResponse.created_at,

      preferences: {
        driver_temperature: DEFAULT_DRIVER_TEMPERATURE,
        passenger_temperature: DEFAULT_PASSENGER_TEMPERATURE,
        driver_seat_heating: DEFAULT_DRIVER_SEAT_HEATING,
        passenger_seat_heating: DEFAULT_PASSENGER_SEAT_HEATING,
        fan_speed: DEFAULT_FAN_SPEED,
        volume: DEFAULT_VOLUME,
        ambient_light: DEFAULT_AMBIENT_LIGHT,
      },
    };

    onUserChange(user);

    closeModal();
  } catch (error) {
    if (error instanceof Error) {
      setAuthError(error.message);
    } else {
      setAuthError(
        "Authentication failed."
      );
    }
  } finally {
    setIsAuthLoading(false);
  }
}

  function logout() {
    clearAuthPersistence();
    onUserChange(null);
    setName("");
    setEmail("");
    setPassword("");
    setAuthError("");
    setIsMenuOpen(false);
    setIsModalOpen(false);
    setVoiceError("");
    setVoiceMessage("");
    setVoiceSamples([]);
    setVoicePhraseIndex(0);
    setIsVoiceModalOpen(false);
  }

  function requestDeleteAccount() {
    if (!currentUser || isDeleteLoading) {
      return;
    }

    setDeleteError("");
    setDeleteResult(null);
    setIsDeleteModalOpen(true);
    setIsMenuOpen(false);
  }

  function closeDeleteModal() {
    if (isDeleteLoading) {
      return;
    }

    setIsDeleteModalOpen(false);
    setDeleteResult(null);
    setDeleteError("");
  }

  async function deleteAccount() {
    if (!currentUser || isDeleteLoading) {
      return;
    }

    setDeleteError("");
    setIsDeleteLoading(true);

    try {
      await deleteUser(currentUser.user_id);
      setDeleteResult("success");
      onUserChange(null);
      setIsMenuOpen(false);
    } catch {
      setDeleteResult("error");
      setDeleteError(
        "Your account could not be deleted."
      );
    } finally {
      setIsDeleteLoading(false);
    }
  }

  async function startVoiceRecording() {
    if (!currentUser) {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError("Browser-ul nu permite înregistrarea audio.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const preferredMimeType = "audio/webm;codecs=opus";
      const mimeType = MediaRecorder.isTypeSupported(
        preferredMimeType
      )
        ? preferredMimeType
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      voiceChunksRef.current = [];
      voiceRecorderRef.current = recorder;
      voiceStreamRef.current = stream;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          voiceChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(voiceChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        setVoiceSamples((previousSamples) => [...previousSamples, blob]);
        setVoicePhraseIndex((previousIndex) => previousIndex + 1);
        setIsVoiceRecording(false);
        setVoiceMessage(
          `Fragment înregistrat: ${Math.min(
            voicePhraseIndex + 1,
            voicePhrases.length
          )}/${voicePhrases.length}`
        );

        stream.getTracks().forEach((track) => track.stop());
        voiceStreamRef.current = null;
        voiceRecorderRef.current = null;
      };

      recorder.start();
      setIsVoiceRecording(true);
      setVoiceError("");
      setVoiceMessage(
        `Înregistrezi fraza ${voicePhraseIndex + 1}/${voicePhrases.length}`
      );
    } catch {
      setVoiceError("Nu am putut accesa microfonul.");
      setIsVoiceRecording(false);
    }
  }

  function stopVoiceRecording() {
    const recorder = voiceRecorderRef.current;

    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
      return;
    }

    voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    voiceStreamRef.current = null;
    voiceRecorderRef.current = null;
    setIsVoiceRecording(false);
  }

  async function submitVoiceEnrollment() {
    if (!currentUser) {
      return;
    }

    if (voiceSamples.length < 3) {
      setVoiceError("Trebuie să înregistrezi cel puțin 3 fraze.");
      return;
    }

    setVoiceError("");
    setVoiceMessage("Se trimite profilul vocal...");

    try {
      const result = await enrollVoiceProfile(
        currentUser.user_id,
        voiceSamples
      );

      const updatedUser: UserProfile = {
        ...currentUser,
        voice_enrolled: result.voice_enrolled,
      };

      saveLocalUser(updatedUser);
      onUserChange(updatedUser);
      setIsVoiceModalOpen(false);
      setVoiceSamples([]);
      setVoicePhraseIndex(0);
      setVoiceMessage("Voice profile configured");
    } catch (error) {
      setVoiceError(
        error instanceof Error
          ? error.message
          : "Nu am putut salva profilul vocal."
      );
    }
  }

  function resetVoiceModal() {
    setVoiceSamples([]);
    setVoicePhraseIndex(0);
    setVoiceError("");
    setVoiceMessage("");
    setIsVoiceRecording(false);
    stopVoiceRecording();
  }

  return (
    <>
      <div
        ref={accountMenuRef}
        className="account-menu-container"
      >
        <button
          className="account-trigger"
          onClick={() => {
            if (!currentUser) {
              openModal("signup");
              return;
            }

            setIsMenuOpen(
              (isOpen) => !isOpen
            );
          }}
        >
          <span className="account-avatar">
            {currentUser
              ? currentUser.name
                  .charAt(0)
                  .toUpperCase()
              : "●"}
          </span>

          <span className="account-current-name">
            {currentUser?.name ?? "Guest"}
          </span>

          <span className="account-arrow">
            {isMenuOpen ? "⌃" : "⌄"}
          </span>
        </button>

        {isMenuOpen && (
          <div className="account-dropdown">
            <div className="account-dropdown-title">
              {currentUser
                ? "Current profile"
                : "Account"}
            </div>

            {currentUser ? (
              <>
                <div className="account-profile-summary">
                  <strong>
                    {currentUser.name}
                  </strong>

                  <small>
                    {currentUser.email}
                  </small>

                  <small>
                    ID:{" "}
                    {currentUser.user_id.slice(
                      0,
                      8
                    )}
                  </small>
                </div>

                <div className="account-role-title">
                  Role in current session
                </div>

                <button
                  type="button"
                  className="account-edit-preferences"
                  onClick={() => {
                    onEditPreferences();
                    setIsMenuOpen(false);
                  }}
                >
                  Edit preferences
                </button>

                <button
                  className={`account-profile-option ${
                    sessionRole === "driver"
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    onRoleChange("driver")
                  }
                >
                  <span className="small-account-avatar">
                    ●
                  </span>

                  <span>Driver</span>

                  {sessionRole ===
                    "driver" && (
                    <span className="account-check">
                      ✓
                    </span>
                  )}
                </button>

                <button
                  className={`account-profile-option ${
                    sessionRole === "passenger"
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    onRoleChange("passenger")
                  }
                >
                  <span className="small-account-avatar">
                    ●
                  </span>

                  <span>Passenger</span>

                  {sessionRole ===
                    "passenger" && (
                    <span className="account-check">
                      ✓
                    </span>
                  )}
                </button>

                <div className="account-voice-status">
                  <span>
                    Voice profile:{" "}
                    {currentUser.voice_enrolled
                      ? "configured"
                      : "not configured"}
                  </span>

                  <button
                    type="button"
                    onClick={() => {
                      resetVoiceModal();
                      setIsVoiceModalOpen(true);
                      setIsMenuOpen(false);
                    }}
                  >
                    {currentUser.voice_enrolled
                      ? "Reconfigure voice profile"
                      : "Configure voice profile"}
                  </button>
                </div>

                <div className="profile-account-actions">
                  <button
                    className="delete-account-button"
                    onClick={requestDeleteAccount}
                    disabled={isDeleteLoading}
                  >
                    {isDeleteLoading
                      ? "Deleting..."
                      : "Delete account"}
                  </button>

                  <button
                    className="add-account-button logout-button"
                    onClick={logout}
                  >
                    Log out
                  </button>
                </div>
              </>
            ) : (
              <button
                className="add-account-button"
                onClick={() =>
                  openModal("login")
                }
              >
                <span className="add-account-icon">
                  ＋
                </span>

                <span>
                  Log in or create account
                </span>
              </button>
            )}
          </div>
        )}
      </div>

      {isVoiceModalOpen && (
        <div
          className="auth-modal-backdrop"
          onClick={() => {
            stopVoiceRecording();
            setIsVoiceModalOpen(false);
          }}
        >
          <div
            className="auth-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <button
              className="auth-modal-close"
              onClick={() => {
                stopVoiceRecording();
                setIsVoiceModalOpen(false);
              }}
            >
              ×
            </button>

            <div className="auth-logo">✦</div>
            <h2>Voice profile setup</h2>
            <p className="auth-description">
              {voicePhraseIndex < voicePhrases.length
                ? `Phrase ${voicePhraseIndex + 1}/${voicePhrases.length}`
                : "Review the recordings"}
            </p>

            <div className="auth-field">
              <span>
                {voicePhraseIndex < voicePhrases.length
                  ? voicePhrases[voicePhraseIndex]
                  : "All set to send to the backend."}
              </span>
            </div>

            {voiceMessage && (
              <p className="auth-error">
                {voiceMessage}
              </p>
            )}

            {voiceError && (
              <p className="auth-error">
                {voiceError}
              </p>
            )}

            <div className="auth-field">
              <span>
                Recorded clips: {voiceSamples.length}/{voicePhrases.length}
              </span>
            </div>

            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              {voicePhraseIndex < voicePhrases.length && (
                <button
                  type="button"
                  className="auth-continue-button"
                  onClick={() => {
                    if (isVoiceRecording) {
                      stopVoiceRecording();
                      return;
                    }

                    void startVoiceRecording();
                  }}
                >
                  {isVoiceRecording
                    ? "Stop recording"
                    : "Record phrase"}
                </button>
              )}

              {voiceSamples.length >= 3 && voicePhraseIndex >= voicePhrases.length && (
                <button
                  type="button"
                  className="auth-continue-button"
                  onClick={() => void submitVoiceEnrollment()}
                >
                  Save voice profile
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {isModalOpen && (
        <div
          className="auth-modal-backdrop"
          onMouseDown={
            handleAuthBackdropMouseDown
          }
          onClick={handleAuthBackdropClick}
        >
          <div
            className="auth-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <button
              className="auth-modal-close"
              onClick={closeModal}
            >
              ×
            </button>

            <div className="auth-logo">
              ✦
            </div>

            <h2>
              {authMode === "login"
                ? "Welcome back"
                : "Create an account"}
            </h2>

            <p className="auth-description">
              {authMode === "login"
                ? "Log in to your personal driving profile."
                : "Create a profile for a personalized drive."}
            </p>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void submitAuth();
              }}
            >
              <div className="auth-tabs">
              <button
                type="button"
                className={
                  authMode === "signup"
                    ? "auth-tab active"
                    : "auth-tab"
                }
                onClick={() =>
                  setAuthMode("signup")
                }
              >
                Sign up
              </button>

              <button
                type="button"
                className={
                  authMode === "login"
                    ? "auth-tab active"
                    : "auth-tab"
                }
                onClick={() =>
                  setAuthMode("login")
                }
              >
                Log in
              </button>
              </div>

            {authMode === "signup" && (
              <label className="auth-field">
                <span>Name</span>

                <input
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  type="text"
                  placeholder="Your Name"
                />
              </label>
            )}

            <label className="auth-field">
              <span>Email</span>

              <input
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                type="email"
                placeholder="email@example.com"
              />
            </label>

            <label className="auth-field">
              <span>Password</span>

              <input
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                type="password"
                placeholder="••••••••••"
              />
            </label>

            {authError && (
              <p className="auth-error">
                {authError}
              </p>
            )}

              <button
              type="submit"
              className="auth-continue-button"
              disabled={isAuthLoading}
            >
              {isAuthLoading
                ? "Logging..."
                : authMode === "login"
                  ? "Log in"
                  : "Create account"}
              </button>

              <p className="auth-footer">
                Your driving profile is linked to your account.
              </p>
            </form>
          </div>
        </div>
      )}

      {isDeleteModalOpen && (
        <div
          className="auth-modal-backdrop"
          onClick={closeDeleteModal}
        >
          <div
            className="auth-modal delete-confirm-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <button
              className="auth-modal-close"
              onClick={closeDeleteModal}
              disabled={isDeleteLoading}
            >
              ×
            </button>

            {deleteResult ? (
              <>
                <div
                  className={
                    deleteResult === "success"
                      ? "auth-logo delete-success-logo"
                      : "auth-logo delete-confirm-logo"
                  }
                >
                  {deleteResult === "success"
                    ? "✓"
                    : "!"}
                </div>

                <h2>
                  {deleteResult === "success"
                    ? "Account deleted"
                    : "Delete account"}
                </h2>

                <p className="auth-description">
                  {deleteResult === "success"
                    ? "Your account has been successfully deleted!"
                    : deleteError}
                </p>

                <button
                  type="button"
                  className={
                    "delete-cancel-button delete-result-button"
                  }
                  onClick={closeDeleteModal}
                >
                  Close
                </button>
              </>
            ) : (
              <>
                <div className="auth-logo delete-confirm-logo">
                  !
                </div>

                <h2>Delete account</h2>

                <p className="auth-description">
                  Are you sure you want to delete the account{" "}
                  {currentUser?.name}?
                </p>

                <div className="delete-warning">
                  <span className="delete-warning-icon">
                    i
                  </span>
                  <span>
                    This action cannot be undone.
                  </span>
                </div>

                <div className="delete-confirm-actions">
                  <button
                    type="button"
                    className="delete-cancel-button"
                    onClick={closeDeleteModal}
                    disabled={isDeleteLoading}
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    className="delete-confirm-button"
                    onClick={() => void deleteAccount()}
                    disabled={isDeleteLoading}
                  >
                    {isDeleteLoading
                      ? "Deleting..."
                      : "Delete account"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default AccountMenu;
