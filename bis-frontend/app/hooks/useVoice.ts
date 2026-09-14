'use client';

import { useState, useCallback, useRef } from 'react';

type RecordingState = 'idle' | 'recording' | 'processing' | 'error';

export function useVoice() {
  const [state, setState] = useState<RecordingState>('idle');
  const [transcript, setTranscript] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        setState('processing');
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        // TODO: send blob to backend STT endpoint
        // const text = await transcribeAudio(blob);
        // setTranscript(text);
        setState('idle');
        stream.getTracks().forEach(t => t.stop());
      };

      recorder.start(250);
      setState('recording');
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Microphone access denied';
      setError(msg);
      setState('error');
    }
  }, []);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setState('processing');
  }, []);

  const reset = useCallback(() => {
    setTranscript('');
    setError(null);
    setState('idle');
  }, []);

  return { state, transcript, error, startRecording, stopRecording, reset };
}
