"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Film, Heart, Settings, Youtube, ArrowLeft, Bell, BellOff } from 'lucide-react';

export default function AuraHome() {
  const [view, setView] = useState<'home' | 'meds'>('home');
  const [isListening, setIsListening] = useState(false);
  const [activeMode, setActiveMode] = useState<'movie' | 'youtube' | null>(null);
  const [statusText, setStatusText] = useState("AURA готова");
  const [heardText, setHeardText] = useState("");
  const [serverIp, setServerIp] = useState("127.0.0.1");
  const [medsSchedule, setMedsSchedule] = useState("");
  const [remindersActive, setRemindersActive] = useState(false);

  // Реф для керування розпізнаванням (щоб уникнути крашів)
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);

    // Очищення при розмонтуванні
    return () => {
      if (recognitionRef.current) recognitionRef.current.stop();
    };
  }, []);

  const saveIp = () => {
    const ip = prompt("Введіть IP Termux (наприклад, 192.168.1.5):", serverIp);
    if (ip) {
      setServerIp(ip);
      localStorage.setItem('aura_server_ip', ip);
    }
  };

  const openMeds = async () => {
    try {
      const response = await fetch(`http://${serverIp}:8000/get-meds-schedule`);
      const data = await response.json();
      setMedsSchedule(data.schedule);
      setRemindersActive(data.enabled);
      setView('meds');
    } catch (e) {
      alert("Помилка зв'язку з сервером Termux. Перевірте IP.");
    }
  };

  const handleBack = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
    setView('home');
  };

  const startVoice = (mode: 'movie' | 'youtube') => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Ваш браузер не підтримує розпізнавання голосу");
      return;
    }

    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = 'uk-UA';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      setIsListening(true);
      setActiveMode(mode);
      setHeardText("");
    };

    recognition.onresult = async (event: any) => {
      const text = event.results[0][0].transcript;
      setHeardText(text);
      const q = text.toLowerCase().replace(/(включи|запусти|знайди|фільм|ютуб|youtube)/g, "").trim();

      if (mode === 'movie') {
        setStatusText(`Шукаю: ${q}`);
        try {
          const res = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(q)}`);
          const data = await res.json();
          setStatusText(data.found ? `✅ Грає: ${data.filename}` : "❌ Не знайдено");
        } catch (err) {
          setStatusText("❌ Помилка сервера");
        }
      } else {
        window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`, "_blank");
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      setActiveMode(null);
    };

    recognition.onerror = () => {
      setIsListening(false);
      setActiveMode(null);
    };

    recognition.start();
  };

  // --- ЕКРАН ЛІКІВ ---
  if (view === 'meds') {
    return (
      <main className="h-screen w-full bg-slate-950 text-white p-2 flex flex-col gap-2 overflow-hidden">
        <div className="h-[20vh] flex gap-2">
          {!remindersActive ? (
            <button 
              onClick={async () => {
                await fetch(`http://${serverIp}:8000/enable-reminders`, {method: 'POST'});
                setRemindersActive(true);
                alert("ТЕСТ ЗАПУЩЕНО! Голос спрацює за 30 секунд.");
              }}
              className="flex-1 bg-blue-600 rounded-3xl border-4 border-blue-400 text-2xl font-black uppercase flex items-center justify-center gap-2"
            >
              <Bell size={32} /> УВІМКНУТИ
            </button>
          ) : (
            <>
              <div className="flex-[2] bg-green-600 rounded-3xl border-4 border-green-400 text-xl font-black uppercase flex items-center justify-center gap-2">
                <Bell size={32} /> ПРАЦЮЄ
              </div>
              <button 
                onClick={async () => {
                  await fetch(`http://${serverIp}:8000/disable-reminders`, {method: 'POST'});
                  setRemindersActive(false);
                }}
                className="flex-1 bg-red-600 rounded-3xl border-4 border-red-400 text-sm font-black uppercase flex flex-col items-center justify-center"
              >
                <BellOff size={24} /> ВИМКНУТИ
              </button>
            </>
          )}
        </div>

        <div className="flex-1 bg-slate-900 rounded-3xl p-4 border-2 border-blue-900 overflow-y-auto">
          <pre className="text-xl font-bold whitespace-pre-wrap leading-tight text-slate-100">
            {medsSchedule}
          </pre>
        </div>

        <button 
          onClick={handleBack}
          className="h-[10vh] bg-slate-800 rounded-3xl text-xl font-bold uppercase flex items-center justify-center gap-4 border-2 border-slate-700"
        >
          <ArrowLeft size={32} /> Назад в меню
        </button>
      </main>
    );
  }

  // --- ГОЛОВНИЙ ЕКРАН ---
  return (
    <main className="h-screen w-full bg-slate-950 text-white p-2 flex flex-col gap-2 overflow-hidden">
      <div className="h-[10vh] flex justify-between items-center px-4 bg-slate-900 rounded-3xl border border-slate-800">
        <h1 className="text-3xl font-black text-blue-500 tracking-tighter uppercase">AURA</h1>
        <button onClick={saveIp} className="p-3 bg-slate-800 rounded-full border border-slate-700 active:bg-slate-700">
          <Settings size={28} />
        </button>
      </div>

      <div className="h-[12vh] bg-blue-900/20 border-l-4 border-blue-600 p-4 rounded-3xl flex flex-col justify-center shadow-xl">
        <p className="text-xl font-bold leading-tight">{statusText}</p>
        {heardText && <p className="text-green-400 italic">"{heardText}"</p>}
      </div>

      <div className="flex-1 flex flex-col gap-2">
        <button 
          onClick={() => startVoice('movie')}
          className={`flex-[2] rounded-[40px] border-8 flex flex-col items-center justify-center active:scale-95 shadow-2xl transition-all ${
            isListening && activeMode === 'movie' ? 'bg-green-600 border-green-400 animate-pulse' : 'bg-blue-600 border-blue-500'
          }`}
        >
          <Film size={80} />
          <span className="text-4xl font-black mt-2 uppercase tracking-widest">ФІЛЬМИ</span>
        </button>

        <button 
          onClick={openMeds}
          className="flex-[2] bg-red-600 rounded-[40px] border-8 border-red-400 flex flex-col items-center justify-center active:scale-95 shadow-2xl"
        >
          <Heart size={80} fill="white" />
          <span className="text-4xl font-black mt-2 uppercase tracking-widest text-center">ЛІКИ</span>
        </button>

        <button 
          onClick={() => startVoice('youtube')}
          className={`flex-1 rounded-[30px] border-4 flex items-center justify-center gap-4 active:scale-95 shadow-lg transition-all ${
            isListening && activeMode === 'youtube' ? 'bg-green-600 border-green-400 animate-pulse' : 'bg-slate-800 border-slate-700'
          }`}
        >
          <Youtube size={40} />
          <span className="text-2xl font-black uppercase">YouTube</span>
        </button>
      </div>
    </main>
  );
}