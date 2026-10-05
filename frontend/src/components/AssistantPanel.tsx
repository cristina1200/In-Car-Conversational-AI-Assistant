import {
  useEffect,
  useRef,
} from "react";

import type {
  ChangeEvent,
  FormEvent,
} from "react";

import "./AssistantPanel.css";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  allowed?: boolean;
}

interface AssistantPanelProps {
  messages: ChatMessage[];
  message: string;
  isLoading: boolean;
  error: string;
  isListening: boolean;
  onStartListening: () => Promise<void>;
  onStopListening: () => void;
  onMessageChange: (
    event: ChangeEvent<HTMLInputElement>
  ) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onQuickCommand: (command: string) => void;
}

function AssistantPanel({
  messages,
  message,
  isLoading,
  error,
  isListening,
  onStartListening,
  onStopListening,
  onMessageChange,
  onSubmit,
  onQuickCommand,
}: AssistantPanelProps) {
  const chatAreaRef =
    useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chatArea = chatAreaRef.current;

    if (!chatArea) {
      return;
    }

    chatArea.scrollTo({
      top: chatArea.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  function handleMicrophoneClick() {
    if (isListening) {
      onStopListening();
    } else {
      void onStartListening();
    }
  }

  return (
    <aside className="assistant-panel">
      <div className="assistant-header">
        <div className="assistant-avatar">✦</div>

        <div>
          <p className="assistant-label">DavaMate</p>

          <h2>Always here for a better drive.</h2>
        </div>
      </div>

      <div
        ref={chatAreaRef}
        className="chat-area"
      >
        {messages.map((chatMessage) => (
          <div
            key={chatMessage.id}
            className={`chat-message ${chatMessage.role}`}
          >
            <div className="message-avatar">
              {chatMessage.role === "user"
                ? "●"
                : "✦"}
            </div>

            <div
              className={`message-bubble ${
                chatMessage.allowed === false
                  ? "message-error"
                  : ""
              }`}
            >
              <p>{chatMessage.text}</p>

              {chatMessage.role === "assistant" &&
                chatMessage.allowed === false && (
                  <span className="blocked-label">
                    Comanda nu a fost acceptată.
                  </span>
                )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="typing-indicator">
            Loading...
          </div>
        )}
      </div>

      <div className="quick-actions">
        <p>Choose a quick command</p>

        <button
          type="button"
          onClick={() =>
            onQuickCommand("Dă muzica mai tare")
          }
        >
          ♫ Dă muzica mai tare
        </button>

        <button
          type="button"
          onClick={() =>
            onQuickCommand(
              "Setează temperatura la 24 de grade"
            )
          }
        >
          ♨ Setează temperatura la 24°
        </button>

        <button
          type="button"
          onClick={() =>
            onQuickCommand(
              "Pornește încălzirea scaunului la treapta 2"
            )
          }
        >
          🪑 Încălzește scaunul
        </button>
      </div>

      {error && (
        <div className="assistant-error">
          {error}
        </div>
      )}

      <form
        className="message-form"
        onSubmit={onSubmit}
      >
        <button
          type="button"
          className={`microphone-button ${
            isListening ? "listening" : ""
          }`}
          title={
            isListening
              ? "Stop listening"
              : "Start voice input"
          }
          onClick={handleMicrophoneClick}
          disabled={isLoading}
        >
          {isListening ? "⏹" : "🎙"}
        </button>

        <input
          value={message}
          onChange={onMessageChange}
          placeholder={
            isListening
              ? "Listening..."
              : "Say something..."
          }
          disabled={isLoading || isListening}
        />

        <button
          type="submit"
          className="send-button"
          disabled={
            isLoading || !message.trim()
          }
        >
          ➤
        </button>
      </form>
    </aside>
  );
}

export default AssistantPanel;
