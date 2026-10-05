import type {
  AssistantRequest,
  AssistantResponse,
  ParticipantCreateRequest,
  ProfileActivationRequest,
  ProfileCreateRequest,
  ProfileResponse,
  ProfileUpdateRequest,
  SessionCreateRequest,
  SessionParticipant,
  SessionRole,
  UserCreateRequest,
  UserLoginRequest,
  UserResponse,
  VehicleSession,
  VehicleState,
  VoiceEnrolledUser,
  VoiceIdentificationResponse,
} from "../types";

const API_URL =
  "http://127.0.0.1:8000";

async function requestJson<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    }
  );

  if (!response.ok) {
    let errorMessage =
      `Request failed: ${response.status}`;

    try {
      const errorData =
        await response.json();

      if (errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      // Se păstrează mesajul implicit.
    }

    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/* VEHICLE */

export async function getVehicleState(): Promise<VehicleState> {
  return requestJson<VehicleState>(
    "/vehicle/state"
  );
}

export async function resetVehicle(): Promise<VehicleState> {
  return requestJson<VehicleState>(
    "/vehicle/reset",
    {
      method: "POST",
    }
  );
}

/* ASSISTANT */

export async function sendAssistantMessage(
  request: AssistantRequest
): Promise<AssistantResponse> {
  return requestJson<AssistantResponse>(
    "/assistant/message",
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function enrollVoiceProfile(
  userId: string,
  files: Blob[]
): Promise<{ user_id: string; voice_enrolled: boolean; recordings: number }> {
  const formData = new FormData();

  files.forEach((file, index) => {
    formData.append(
      "files",
      file,
      `voice-${index + 1}.wav`
    );
  });

  const response = await fetch(
    `${API_URL}/users/${encodeURIComponent(userId)}/voice/enroll`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    let detail = "Voice enrollment failed.";

    try {
      const errorData = await response.json();
      detail = errorData.detail ?? detail;
    } catch {
      // noop
    }

    throw new Error(detail);
  }

  return response.json() as Promise<{
    user_id: string;
    voice_enrolled: boolean;
    recordings: number;
  }>;
}

/* WHISPER - NU MODIFICĂM FLUXUL */

export async function transcribeAudio(
  audioBlob: Blob
): Promise<string> {
  const formData = new FormData();

  formData.append(
    "file",
    audioBlob,
    "speech.webm"
  );

  const response = await fetch(
    `${API_URL}/speech/transcribe`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    let detail =
      "Transcrierea audio a eșuat.";

    try {
      const errorData =
        await response.json();

      detail =
        errorData.detail ?? detail;
    } catch {
      // Mesaj implicit.
    }

    throw new Error(detail);
  }

  const data: { text: string } =
    await response.json();

  return data.text;
}

export async function identifyVoiceSpeaker(
  audioBlob: Blob,
  sessionId: string
): Promise<VoiceIdentificationResponse> {
  const formData = new FormData();

  formData.append(
    "file",
    audioBlob,
    "voice.webm"
  );

  formData.append("session_id", sessionId);

  const response = await fetch(
    `${API_URL}/voice/identify`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    let detail =
      "Identificarea vocii a eșuat.";

    try {
      const errorData =
        await response.json();

      detail =
        errorData.detail ?? detail;
    } catch {
      // Mesaj implicit.
    }

    throw new Error(detail);
  }

  return response.json() as Promise<VoiceIdentificationResponse>;
}

export async function listVoiceEnrolledUsers(): Promise<VoiceEnrolledUser[]> {
  return requestJson<VoiceEnrolledUser[]>("/users/voice-enrolled");
}

/* USERS */

export async function createUser(
  request: UserCreateRequest
): Promise<UserResponse> {
  return requestJson<UserResponse>(
    "/users",
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function loginUser(
  request: UserLoginRequest
): Promise<UserResponse> {
  return requestJson<UserResponse>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function getUser(
  userId: string
): Promise<UserResponse> {
  return requestJson<UserResponse>(
    `/users/${userId}`
  );
}

export async function deleteUser(
  userId: string
): Promise<void> {
  await requestJson<void>(
    `/users/${userId}`,
    {
      method: "DELETE",
    }
  );
}

/* PROFILES */

export async function createProfile(
  request: ProfileCreateRequest
): Promise<ProfileResponse> {
  return requestJson<ProfileResponse>(
    "/profiles",
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function getProfiles(
  userId: string
): Promise<ProfileResponse[]> {
  return requestJson<ProfileResponse[]>(
    `/profiles?user_id=${encodeURIComponent(
      userId
    )}`
  );
}

export async function getProfile(
  profileId: string,
  userId: string
): Promise<ProfileResponse> {
  return requestJson<ProfileResponse>(
    `/profiles/${profileId}?user_id=${encodeURIComponent(
      userId
    )}`
  );
}

export async function updateProfile(
  profileId: string,
  userId: string,
  request: ProfileUpdateRequest
): Promise<ProfileResponse> {
  return requestJson<ProfileResponse>(
    `/profiles/${profileId}?user_id=${encodeURIComponent(
      userId
    )}`,
    {
      method: "PUT",
      body: JSON.stringify(request),
    }
  );
}

/* SESSIONS */

export async function createSession(
  request: SessionCreateRequest
): Promise<VehicleSession> {
  return requestJson<VehicleSession>(
    "/sessions",
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function ensureSessionForUser(
  userId: string,
  preferredRole: SessionRole = "driver"
): Promise<VehicleSession> {
  const createdSession = await createSession({
    created_by_user_id: userId,
  });

  const participant = await addSessionParticipant(
    createdSession.session_id,
    {
      user_id: userId,
      role: preferredRole,
    }
  );

  return {
    ...createdSession,
    participants: [
      ...(createdSession.participants ?? []),
      {
        user_id: participant.user_id,
        role: participant.role,
        session_id: createdSession.session_id,
      },
    ],
  };
}

export async function addSessionParticipant(
  sessionId: string,
  request: ParticipantCreateRequest
): Promise<SessionParticipant> {
  return requestJson<SessionParticipant>(
    `/sessions/${sessionId}/participants`,
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function updateSessionParticipantRole(
  sessionId: string,
  userId: string,
  role: SessionRole
): Promise<SessionParticipant> {
  return requestJson<SessionParticipant>(
    `/sessions/${sessionId}/participants/${encodeURIComponent(userId)}`,
    {
      method: "PUT",
      body: JSON.stringify({ role }),
    }
  );
}

export async function removeSessionParticipant(
  sessionId: string,
  userId: string
): Promise<void> {
  await requestJson<void>(
    `/sessions/${sessionId}/participants/${encodeURIComponent(userId)}`,
    { method: "DELETE" }
  );
}

export async function getSession(
  sessionId: string
): Promise<VehicleSession> {
  return requestJson<VehicleSession>(
    `/sessions/${sessionId}`
  );
}

export async function activateSessionProfile(
  sessionId: string,
  request: ProfileActivationRequest
): Promise<SessionParticipant> {
  return requestJson<SessionParticipant>(
    `/sessions/${sessionId}/profile`,
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export async function closeSession(
  sessionId: string
): Promise<VehicleSession> {
  return requestJson<VehicleSession>(
    `/sessions/${sessionId}/close`,
    {
      method: "POST",
    }
  );
}
