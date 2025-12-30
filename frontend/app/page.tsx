"use client";

import React, { useState, useEffect } from 'react';
import { Film, Heart, Settings, Youtube, ArrowLeft, Bell, BellOff } from 'lucide-react';

export default function AuraHome() {
  const [view, setView] = useState<'home' | 'meds'>('home');
  const [statusText, setStatusText] = useState("AURA готова");
  const [serverIp, setServerIp] = useState("127.0.0.1");
  const [medsSchedule, setMedsSchedule] = useState("");
  const [remindersActive, setRemindersActive] = useState(false);

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);
  }, []);

  const saveIp = () => {
    const ip = prompt("Введите IP Termux:", serverIp);
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
      alert("Ошибка связи с сервером Termux");
    }
  };

  const enableReminders = async () => {
    try {
      await fetch(`http://${serverIp}:8000/enable-reminders`, { method: 'POST' });
      setRemindersActive(true);
      alert("ТЕСТ ЗАПУЩЕН! Напоминание сработает через 30 секунд.");
    } catch (e) {
      alert("Ошибка включения");
    }
  };

  const disableReminders = async () => {
    try {
      await fetch(`http://${serverIp}:8000/disable-reminders`, { method: 'POST' });
      setRemindersActive(false);
    } catch (e) {
      alert("Ошибка выключения");
    }
  };

  // --- ЭКРАН ГРАФИКА ПРИЕМА ---
  if (view === 'meds') {
    return (
      <main className="h-screen w-full bg-slate-950 text-white p-2 flex flex-col gap-2 overflow-hidden">
        {/* ВЕРХНЯЯ ПАНЕЛЬ УПРАВЛЕНИЯ (20% высоты) */}
        <div className="h-[20vh] flex gap-2">
          {!remindersActive ? (
            <button 
              onClick={enableReminders}
              className="flex-1 bg-blue-600 rounded-3xl border-4 border-blue-400 text-2xl font-black uppercase flex items-center justify-center gap-2"
            >
              <Bell size={32} /> Включить
            </button>
          ) : (
            <>
              <div className="flex-[2] bg-green-600 rounded-3xl border-4 border-green-400 text-xl font-black uppercase flex items-center justify-center gap-2">
                <Bell size={32} /> Работает
              </div>
              <button 
                onClick={disableReminders}
                className="flex-1 bg-red-600 rounded-3xl border-4 border-red-400 text-sm font-black uppercase flex flex-col items-center justify-center"
              >
                <BellOff size={24} /> ВЫКЛЮЧИТЬ
              </button>
            </>
          )}
        </div>

        {/* ГРАФИК (ГИБКИЙ БЛОК) */}
        <div className="flex-1 bg-slate-900 rounded-3xl p-4 border-2 border-blue-900 overflow-y-auto shadow-inner">
          <pre className="text-xl font-bold whitespace-pre-wrap leading-snug">
            {medsSchedule}
          </pre>
        </div>

        {/* КНОПКА НАЗАД (10% высоты) */}
        <button 
          onClick={() => setView('home')}
          className="h-[10vh] bg-slate-800 rounded-3xl text-xl font-bold uppercase flex items-center justify-center gap-4 border-2 border-slate-700"
        >
          <ArrowLeft size={32} /> Назад в меню
        </button>
      </main>
    );
  }

  // --- ГЛАВНЫЙ ЭКРАН ---
  return (
    <main className="h-screen w-full bg-slate-950 text-white p-2 flex flex-col gap-2 overflow-hidden">
      {/* HEADER */}
      <div className="h-[10vh] flex justify-between items-center px-4 bg-slate-900 rounded-3xl border border-slate-800">
        <h1 className="text-3xl font-black text-blue-500 tracking-tighter">AURA</h1>
        <button onClick={saveIp} className="p-3 bg-slate-800 rounded-full border border-slate-700">
          <Settings size={28} />
        </button>
      </div>

      {/* STATUS */}
      <div className="h-[12vh] bg-blue-900/20 border-l-4 border-blue-600 p-4 rounded-3xl flex items-center">
        <p className="text-xl font-bold leading-tight">{statusText}</p>
      </div>

      {/* BUTTONS GRID */}
      <div className="flex-1 flex flex-col gap-2">
        <button className="flex-[2] bg-blue-600 rounded-[40px] border-8 border-blue-400 flex flex-col items-center justify-center shadow-2xl active:scale-95">
          <Film size={80} />
          <span className="text-4xl font-black mt-2 uppercase tracking-widest">ФИЛЬМЫ</span>
        </button>

        <button 
          onClick={openMeds}
          className="flex-[2] bg-red-600 rounded-[40px] border-8 border-red-400 flex flex-col items-center justify-center shadow-2xl active:scale-95"
        >
          <Heart size={80} fill="white" />
          <span className="text-4xl font-black mt-2 uppercase tracking-widest text-center">ЛЕКАРСТВА</span>
        </button>

        <button 
          onClick={() => window.open('https://youtube.com', '_blank')}
          className="flex-1 bg-slate-800 rounded-[30px] border-4 border-slate-700 flex items-center justify-center gap-4 active:scale-95"
        >
          <Youtube size={40} />
          <span className="text-2xl font-black uppercase">YouTube</span>
        </button>
      </div>
    </main>
  );
}