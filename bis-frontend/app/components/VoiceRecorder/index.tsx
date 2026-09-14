"use client";

import { Mic, MicOff, Loader2 } from "lucide-react";
import { useVoice } from "../../hooks/useVoice";

interface VoiceRecorderProps {
  onTranscript?: (text: string) => void;
}

export default function VoiceRecorder({ onTranscript }: VoiceRecorderProps) {
  const { state, transcript, error, startRecording, stopRecording } = useVoice();

  const isRecording = state === "recording";
  const isProcessing = state === "processing";

  const handleClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        onClick={handleClick}
        disabled={isProcessing}
        aria-label={isRecording ? "Stop recording" : "Start recording"}
        className={`relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg ${
          isRecording
            ? "bg-destructive hover:bg-destructive/90 scale-110"
            : "bg-gov-navy hover:bg-gov-navy/90"
        } disabled:opacity-50`}
      >
        {isProcessing ? (
          <Loader2 className="h-7 w-7 text-white animate-spin" />
        ) : isRecording ? (
          <>
            <span className="absolute inset-0 rounded-full bg-destructive animate-ping opacity-40" />
            <MicOff className="h-7 w-7 text-white relative z-10" />
          </>
        ) : (
          <Mic className="h-7 w-7 text-white" />
        )}
      </button>

      <p className="text-xs text-muted-foreground font-medium">
        {isProcessing
          ? "Processing..."
          : isRecording
          ? "Recording — click to stop"
          : "Click to speak"}
      </p>

      {transcript && (
        <div className="w-full rounded-xl border border-border bg-muted/50 p-3 text-sm text-foreground">
          {transcript}
        </div>
      )}

      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}