"use client";

import React, { useState, useEffect } from 'react';
import { Film, Heart, Settings, Youtube, ArrowLeft } from 'lucide-react';

export default function AuraHome() {
  const [view, setView] = useState<'home' | 'meds'>('home');
  const [isListening, setIsListening] = useState(false);
  const [activeMode, setActiveMode] = useState<'movie' | 'youtube' | null>(null);
  const [statusText, setStatusText] = useState("AURA готова к работе");
  const [heardText, setHeardText] = useState("");
  const [serverIp, setServerIp] = useState("127.0.0.1");
  const [medsSchedule, setMedsSchedule] = useState("");

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) {
      setServerIp(savedIp);
    }
  }, []);

  const saveIp = () => {
    const ip = prompt("Введите IP телефона мамы (из Termux):", serverIp);
    if (ip) {
      setServerIp(ip);
      localStorage.setItem('aura_server_ip', ip);
    }
  };

  // Логика перехода к лекарствам
  const openMeds = async () => {
    try {
      const response = await fetch(`http://${serverIp}:8000/get-meds-schedule`);
      const data = await response.json();
      setMedsSchedule(data.schedule);
      setView('meds');
    } catch (error) {
      alert("Ошибка связи с сервером Termux");
    }
  };

  // Включение напоминаний
  const enableReminders = async () => {
    try {
      await fetch(`http://${serverIp}:8000/enable-reminders`, { method: 'POST' });
      alert("НАПОМИНАНИЯ ВКЛЮЧЕНЫ");
    } catch (error) {
      alert("Не удалось включить");
    }
  };

  const startVoice = (mode: 'movie' | 'youtube') => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';

    recognition.onstart = () => {
      setIsListening(true);
      setActiveMode(mode);
    };

    recognition.onresult = async (event: any) => {
      const text = event.results[0][0].transcript;
      setHeardText(text);
      const cleanQuery = text.toLowerCase().replace(/(включи|запусти|найди|фильм|ютуб|youtube)/g, "").trim();

      if (mode === 'movie') {
        setStatusText(`Ищу фильм: ${cleanQuery}...`);
        const res = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(cleanQuery)}`);
        const data = await res.json();
        setStatusText(data.found ? `✅ Играет: ${data.filename}` : "❌ Фильм не найден");
      } else {
        window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(cleanQuery)}`, "_blank");
      }
      setIsListening(false);
    };

    recognition.start();
  };

  // --- ЭКРАН ПРИЕМА ЛЕКАРСТВ ---
  if (view === 'meds') {
    return (
      <main className="min-h-screen bg-slate-950 text-white p-4 flex flex-col font-sans">
        <button 
          onClick={enableReminders}
          className="w-full py-12 bg-green-600 rounded-[40px] text-4xl font-black uppercase border-8 border-green-400 mb-6 shadow-2xl active:bg-green-700"
        >
          Включить напоминание
        </button>

        <div className="flex-grow bg-slate-900 rounded-[40px] p-8 border-4 border-blue-900 overflow-y-auto mb-6 shadow-inner">
          <pre className="text-3xl font-bold whitespace-pre-wrap leading-tight text-slate-100">
            {medsSchedule}
          </pre>
        </div>

        <button 
          onClick={enableReminders}
          className="w-full py-12 bg-green-600 rounded-[40px] text-4xl font-black uppercase border-8 border-green-400 mb-6 shadow-2xl active:bg-green-700"
        >
          Включить напоминание
        </button>

        <button 
          onClick={() => setView('home')}
          className="w-full py-6 bg-slate-800 rounded-[30px] text-2xl font-bold uppercase flex items-center justify-center gap-4 border-4 border-slate-700"
        >
          <ArrowLeft size={40} /> Назад в меню
        </button>
      </main>
    );
  }

  // --- ГЛАВНЫЙ ЭКРАН ---
  return (
    <main className="min-h-screen bg-slate-950 text-white p-4 font-sans">
      <div className="flex justify-between items-center mb-6 pt-2">
        <h1 className="text-5xl font-black text-blue-500 tracking-tighter">AURA</h1>
        <button onClick={saveIp} className="p-4 bg-slate-800 rounded-full text-slate-400 border-2 border-slate-700">
          <Settings size={40} />
        </button>
      </div>

      <div className="mb-8 bg-slate-900 border-l-8 border-blue-600 p-6 rounded-2xl shadow-xl">
        <p className="text-3xl font-bold leading-tight">{statusText}</p>
        {heardText && <p className="mt-4 text-xl text-green-400 italic">"{heardText}"</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* КНОПКА ФИЛЬМЫ */}
        <button 
          onClick={() => startVoice('movie')} 
          className="col-span-2 py-16 flex flex-col items-center justify-center rounded-[50px] border-8 border-blue-500 bg-blue-600 active:scale-95 shadow-2xl"
        >
          <Film size={120} />
          <span className="text-5xl font-black mt-4 uppercase tracking-widest">ФИЛЬМЫ</span>
        </button>

        {/* КНОПКА ПРИЕМ ЛЕКАРСТВ */}
        <button 
          onClick={openMeds}
          className="col-span-2 py-16 flex flex-col items-center justify-center rounded-[50px] border-8 border-red-500 bg-red-600 active:scale-95 shadow-2xl"
        >
          <Heart size={120} fill="white" />
          <span className="text-5xl font-black mt-4 uppercase tracking-widest text-center">Приём лекарств</span>
        </button>

        {/* КНОПКА YOUTUBE */}
        <button 
          onClick={() => startVoice('youtube')}
          className="col-span-2 py-10 flex flex-col items-center justify-center rounded-[40px] border-8 border-slate-700 bg-slate-800 active:scale-95"
        >
          <Youtube size={80} />
          <span className="text-3xl font-black mt-2 uppercase">YouTube</span>
        </button>
      </div>
    </main>
  );
}