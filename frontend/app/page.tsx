"use client";

import React, { useState, useEffect } from 'react';
import { Film, Heart, Settings, Youtube, ArrowLeft, Bell, BellOff } from 'lucide-react';

export default function AuraHome() {
  const [view, setView] = useState<'home' | 'meds'>('home');
  const [statusText, setStatusText] = useState("AURA готова к работе");
  const [heardText, setHeardText] = useState("");
  const [serverIp, setServerIp] = useState("127.0.0.1");
  const [medsSchedule, setMedsSchedule] = useState("");
  const [remindersActive, setRemindersActive] = useState(false);

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);
  }, []);

  const saveIp = () => {
    const ip = prompt("IP телефона мамы:", serverIp);
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
    } catch (error) {
      alert("Ошибка связи с Termux");
    }
  };

  const enableReminders = async () => {
    try {
      await fetch(`http://${serverIp}:8000/enable-reminders`, { method: 'POST' });
      setRemindersActive(true);
      alert("Тест запущен! Сигнал будет через 30 секунд.");
    } catch (error) {
      alert("Не удалось включить");
    }
  };

  const disableReminders = async () => {
    try {
      await fetch(`http://${serverIp}:8000/disable-reminders`, { method: 'POST' });
      setRemindersActive(false);
    } catch (error) {
      alert("Не удалось выключить");
    }
  };

  const startVoice = (mode: 'movie' | 'youtube') => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.onresult = async (event: any) => {
      const text = event.results[0][0].transcript;
      setHeardText(text);
      const q = text.toLowerCase().replace(/(включи|запусти|найди|фильм|ютуб)/g, "").trim();
      if (mode === 'movie') {
        const res = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(q)}`);
        const data = await res.json();
        setStatusText(data.found ? `✅ Играет: ${data.filename}` : "❌ Не найден");
      } else {
        window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`, "_blank");
      }
    };
    recognition.start();
  };

  const MedControlButtons = () => (
    <div className="flex gap-4 mb-6">
      {!remindersActive ? (
        <button 
          onClick={enableReminders}
          className="flex-grow py-12 bg-blue-600 rounded-[40px] text-4xl font-black uppercase border-8 border-blue-400 shadow-2xl flex items-center justify-center gap-4"
        >
          <Bell size={48} /> Включить напоминание
        </button>
      ) : (
        <>
          <button 
            className="flex-[2] py-12 bg-green-600 rounded-[40px] text-3xl font-black uppercase border-8 border-green-400 shadow-2xl flex items-center justify-center gap-4"
          >
            <Bell size={48} /> Напоминание работает
          </button>
          <button 
            onClick={disableReminders}
            className="flex-1 py-12 bg-red-600 rounded-[40px] text-2xl font-black uppercase border-8 border-red-400 shadow-2xl active:bg-red-700 flex flex-col items-center justify-center"
          >
            <BellOff size={40} /> ВЫКЛЮЧИТЬ
          </button>
        </>
      )}
    </div>
  );

  if (view === 'meds') {
    return (
      <main className="min-h-screen bg-slate-950 text-white p-4 flex flex-col font-sans">
        <MedControlButtons />
        <div className="flex-grow bg-slate-900 rounded-[40px] p-8 border-4 border-blue-900 overflow-y-auto mb-6 shadow-inner">
          <pre className="text-3xl font-bold whitespace-pre-wrap leading-tight text-slate-100">
            {medsSchedule}
          </pre>
        </div>
        <MedControlButtons />
        <button 
          onClick={() => setView('home')}
          className="w-full py-6 bg-slate-800 rounded-[30px] text-2xl font-bold uppercase flex items-center justify-center gap-4 border-4 border-slate-700"
        >
          <ArrowLeft size={40} /> Назад
        </button>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white p-4 font-sans">
      <div className="flex justify-between items-center mb-6 pt-2">
        <h1 className="text-5xl font-black text-blue-500 tracking-tighter">AURA</h1>
        <button onClick={saveIp} className="p-4 bg-slate-800 rounded-full border-2 border-slate-700 text-slate-400"><Settings size={40} /></button>
      </div>
      <div className="mb-8 bg-slate-900 border-l-8 border-blue-600 p-6 rounded-2xl shadow-xl">
        <p className="text-3xl font-bold leading-tight">{statusText}</p>
        {heardText && <p className="mt-4 text-xl text-green-400 italic">"{heardText}"</p>}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => startVoice('movie')} className="col-span-2 py-16 bg-blue-600 rounded-[50px] border-8 border-blue-500 active:scale-95 flex flex-col items-center">
          <Film size={120} /><span className="text-5xl font-black mt-4 uppercase">ФИЛЬМЫ</span>
        </button>
        <button onClick={openMeds} className="col-span-2 py-16 bg-red-600 rounded-[50px] border-8 border-red-500 active:scale-95 flex flex-col items-center">
          <Heart size={120} fill="white" /><span className="text-5xl font-black mt-4 uppercase text-center">Приём лекарств</span>
        </button>
        <button onClick={() => startVoice('youtube')} className="col-span-2 py-10 bg-slate-800 rounded-[40px] border-8 border-slate-700 active:scale-95 flex flex-col items-center">
          <Youtube size={80} /><span className="text-3xl font-black mt-2 uppercase">YouTube</span>
        </button>
      </div>
    </main>
  );
}