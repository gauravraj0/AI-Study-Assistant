import { useRef, useState } from "react";

// Web Speech API — voice questions in the AI tutor chat.
export function useVoice(onFinal) {
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);
  const SR = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const supported = !!SR;

  const start = () => {
    if (!supported || recRef.current) return;
    const rec = new SR();
    rec.lang = navigator.language || "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript;
      if (t) onFinal(t);
    };
    rec.onend = () => {
      setListening(false);
      recRef.current = null;
    };
    rec.onerror = () => {
      setListening(false);
      recRef.current = null;
    };
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stop = () => recRef.current?.stop();

  return { supported, listening, start, stop };
}

// Browser text-to-speech for reading answers aloud.
export function speak(text) {
  if (!("speechSynthesis" in window)) return;
  const clean = text.replace(/[*#_`>\[\]]/g, "").replace(/\n+/g, ". ");
  const u = new SpeechSynthesisUtterance(clean);
  u.rate = 1.02;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}
