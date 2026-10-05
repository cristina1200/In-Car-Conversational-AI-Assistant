import { useRef, useState } from "react";
import { transcribeAudio } from "../services/api";

export function useSpeechRecognition(
  onTranscript: (
    text: string,
    audioBlob: Blob
  ) => void | Promise<void>
) {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const animationFrameRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const recordingStartedAtRef = useRef(0);
  const lastSoundAtRef = useRef(0);
  const speechDetectedRef = useRef(false);

  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState("");

  function stopAudioMonitoring() {
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
  }

  async function startListening() {
    if (recorderRef.current) {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setSpeechError(
        "Browserul nu suporta inregistrarea audio."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          noiseSuppression: true,
          echoCancellation: true,
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
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();

      analyser.fftSize = 2048;
      source.connect(analyser);

      const audioSamples = new Uint8Array(analyser.fftSize);

      chunksRef.current = [];
      streamRef.current = stream;
      recorderRef.current = recorder;
      audioContextRef.current = audioContext;
      recordingStartedAtRef.current = Date.now();
      lastSoundAtRef.current = Date.now();
      speechDetectedRef.current = false;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setSpeechError(
          "A aparut o problema la inregistrarea audio."
        );
        setIsListening(false);
      };

      recorder.onstop = async () => {
        setIsListening(false);
        stopAudioMonitoring();

        const audioBlob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;

        if (audioBlob.size === 0) {
          setSpeechError("Nu a fost inregistrat niciun sunet.");
          return;
        }

        try {
          setSpeechError("");
          const transcript = await transcribeAudio(audioBlob);

          if (!transcript.trim()) {
            setSpeechError("Whisper nu a detectat niciun cuvant.");
            return;
          }

          await onTranscript(
            transcript.trim(),
            audioBlob
          );
        } catch (error) {
          setSpeechError(
            error instanceof Error
              ? error.message
              : "Transcrierea audio a esuat."
          );
        }
      };

      const monitorSilence = () => {
        if (
          recorderRef.current !== recorder ||
          recorder.state === "inactive"
        ) {
          return;
        }

        analyser.getByteTimeDomainData(audioSamples);

        let squareSum = 0;

        for (const sample of audioSamples) {
          const normalizedSample = (sample - 128) / 128;
          squareSum += normalizedSample * normalizedSample;
        }

        const volume = Math.sqrt(
          squareSum / audioSamples.length
        );
        const now = Date.now();

        if (volume > 0.055) {
          speechDetectedRef.current = true;
          lastSoundAtRef.current = now;
        }

        const silenceDuration = now - lastSoundAtRef.current;
        const recordingDuration =
          now - recordingStartedAtRef.current;

        if (
          speechDetectedRef.current &&
          silenceDuration >= 900
        ) {
          recorder.stop();
          return;
        }

        if (recordingDuration >= 10000) {
          recorder.stop();
          return;
        }

        animationFrameRef.current = requestAnimationFrame(
          monitorSilence
        );
      };

      setSpeechError("");
      setIsListening(true);
      recorder.start();
      animationFrameRef.current = requestAnimationFrame(
        monitorSilence
      );
    } catch (error) {
      stopAudioMonitoring();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      recorderRef.current = null;
      setIsListening(false);

      if (
        error instanceof DOMException &&
        error.name === "NotAllowedError"
      ) {
        setSpeechError(
          "Accesul la microfon a fost refuzat."
        );
      } else {
        setSpeechError(
          "Nu am putut porni inregistrarea audio."
        );
      }
    }
  }

  function stopListening() {
    const recorder = recorderRef.current;

    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
      return;
    }

    stopAudioMonitoring();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setIsListening(false);
  }

  return {
    startListening,
    stopListening,
    isListening,
    speechError,
  };
}
