"use client";

import React, { useState, useEffect } from 'react';
import { Film, Phone, Heart, Bell, Settings, Youtube } from 'lucide-react';

export default function AuraHome() {
  const [isListening, setIsListening] = useState(false);
  const [statusText, setStatusText] = useState("Нажмите 'Фильмы'");
  const [serverIp, setServerIp] = useState("127.0.0.1");

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);
  }, []);

  const saveIp = () => {
    const ip = prompt("Введите IP телефона мамы (из Termux):", serverIp);
    if (ip) {
      setServerIp(ip);
      localStorage.setItem('aura_server_ip', ip);
    }
  };

  const playMovie = async (title: string) => {
    setStatusText(`Ищу: ${title}...`);
    try {
      const response = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(title)}`);
      const data = await response.json();
      if (data.found) setStatusText(`Играет: ${data.filename}`);
      else setStatusText("Фильм не найден");
    } catch (error) {
      setStatusText("Нет связи с телефоном!");
    }
    setIsListening(false);
  };

  const handleVoiceInput = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitRecognition;
    if (!SpeechRecognition) {
      setStatusText("Голос не поддерживается");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript.toLowerCase();
      const movieTitle = text.replace(/(включи|запусти|найди|фильм)/g, "").trim();
      playMovie(movieTitle);
    };
    recognition.start();
  };

  // Функция для открытия YouTube (можно доработать на бэкенде позже)
  const openYoutube = () => {
    window.open("https://www.youtube.com", "_blank");
  };

  return (
    // Убрали fixed и overflow-hidden, добавили min-h-screen для прокрутки
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 pb-20 font-sans">
      
      {/* Шапка */}
      <div className="flex justify-between items-center mb-6 pt-2">
        <h1 className="text-4xl font-black text-blue-500 tracking-tighter">AURA</h1>
        <button onClick={saveIp} className="p-4 bg-slate-800 rounded-full text-slate-400">
          <Settings size={30} />
        </button>
      </div>

      {/* Статус */}
      <div className="mb-8 bg-slate-900 border-l-8 border-blue-600 p-6 rounded-2xl shadow-xl">
        <p className="text-xl text-slate-400 mb-1">Статус:</p>
        <p className="text-3xl font-bold leading-tight">{statusText}</p>
      </div>

      {/* Сетка кнопок - теперь их 5 */}
      <div className="grid grid-cols-2 gap-4">
        
        {/* КНОПКА ФИЛЬМЫ */}
        <button 
          onClick={handleVoiceInput} 
          className={`col-span-2 py-12 flex flex-col items-center justify-center rounded-[40px] border-8 transition-all active:scale-95 ${
            isListening ? 'border-green-400 bg-green-900/20 animate-pulse' : 'border-blue-500 bg-blue-600 shadow-lg'
          }`}
        >
          <Film size={100} />
          <span className="text-4xl font-black mt-4 uppercase">ФИЛЬМЫ</span>
        </button>

        {/* КНОПКА ЮТУБ (НОВАЯ) */}
        <button 
          onClick={openYoutube}
          className="aspect-square flex flex-col items-center justify-center rounded-[40px] border-8 border-red-600 bg-red-700 shadow-lg active:scale-95"
        >
          <Youtube size={80} />
          <span className="text-2xl font-black mt-2 uppercase">YouTube</span>
        </button>

        {/* КНОПКА СВЯЗЬ */}
        <button className="aspect-square flex flex-col items-center justify-center rounded-[40px] border-8 border-slate-800 bg-slate-800/50 opacity-50">
          <Phone size={60} />
          <span className="text-2xl font-bold mt-2 uppercase">Связь</span>
        </button>

        {/* КНОПКА ЗДОРОВЬЕ */}
        <button className="aspect-square flex flex-col items-center justify-center rounded-[40px] border-8 border-slate-800 bg-slate-800/50 opacity-50">
          <Heart size={60} />
          <span className="text-2xl font-bold mt-2 uppercase">Здоровье</span>
        </button>

        {/* КНОПКА УТИЛИТЫ */}
        <button className="aspect-square flex flex-col items-center justify-center rounded-[40px] border-8 border-slate-800 bg-slate-800/50 opacity-50">
          <Bell size={60} />
          <span className="text-2xl font-bold mt-2 uppercase">Инфо</span>
        </button>

      </div>
    </main>
  );
}