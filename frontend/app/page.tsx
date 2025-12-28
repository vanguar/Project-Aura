"use client";

import React, { useState, useEffect } from 'react';
import { Film, Phone, Heart, Bell, Settings, Youtube } from 'lucide-react';

export default function AuraHome() {
  const [isListening, setIsListening] = useState(false);
  const [activeMode, setActiveMode] = useState<'movie' | 'youtube' | null>(null);
  const [statusText, setStatusText] = useState("Нажмите 'Фильмы' или 'YouTube'");
  const [serverIp, setServerIp] = useState("127.0.0.1");

  useEffect(() => {
    // Детектор: Ноут или Телефон
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    if (isMobile) {
      const savedIp = localStorage.getItem('aura_server_ip');
      if (savedIp) setServerIp(savedIp);
      else setStatusText("Настройте IP в шестеренке");
    } else {
      // Для ноутбука всегда используем локальный адрес
      setServerIp("127.0.0.1");
      setStatusText("Режим: Ноутбук (127.0.0.1)");
    }
  }, []);

  const saveIp = () => {
    const ip = prompt("Введите IP телефона мамы (из Termux):", serverIp);
    if (ip) {
      setServerIp(ip);
      localStorage.setItem('aura_server_ip', ip);
    }
  };

  // Поиск фильма в локальной сети (Телефон или Ноут)
  const playMovie = async (title: string) => {
    setStatusText(`Ищу фильм: ${title}...`);
    try {
      const response = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(title)}`);
      const data = await response.json();
      if (data.found) setStatusText(`Играет: ${data.filename}`);
      else setStatusText("Фильм не найден в папке");
    } catch (error) {
      const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
      setStatusText(isMobile ? "Нет связи с Termux!" : "Запусти main.py на ноуте!");
    }
    setIsListening(false);
    setActiveMode(null);
  };

  // Поиск на YouTube
  const searchYoutube = (query: string) => {
    setStatusText(`YouTube: ${query}`);
    window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`, "_blank");
    setIsListening(false);
    setActiveMode(null);
  };

  // Универсальный обработчик голоса
  const startVoice = (mode: 'movie' | 'youtube') => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatusText("Голос не поддерживается");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    
    recognition.onstart = () => {
      setIsListening(true);
      setActiveMode(mode);
      setStatusText(mode === 'movie' ? "Какой фильм включить?" : "Что найти на YouTube?");
    };

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript.toLowerCase();
      // Убираем лишние слова-команды
      const cleanQuery = text.replace(/(включи|запусти|найди|фильм|ютуб|youtube)/g, "").trim();
      
      if (mode === 'movie') playMovie(cleanQuery);
      else searchYoutube(cleanQuery);
    };

    recognition.onerror = () => {
      setIsListening(false);
      setStatusText("Ошибка микрофона");
    };

    recognition.start();
  };

  return (
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

      <div className="grid grid-cols-2 gap-4">
        
        {/* ФИЛЬМЫ */}
        <button 
          onClick={() => startVoice('movie')} 
          className={`col-span-2 py-12 flex flex-col items-center justify-center rounded-[40px] border-8 transition-all active:scale-95 ${
            isListening && activeMode === 'movie' ? 'border-green-400 bg-green-900/20 animate-pulse' : 'border-blue-500 bg-blue-600 shadow-lg'
          }`}
        >
          <Film size={100} />
          <span className="text-4xl font-black mt-4 uppercase">ФИЛЬМЫ</span>
        </button>

        {/* YOUTUBE */}
        <button 
          onClick={() => startVoice('youtube')}
          className={`aspect-square flex flex-col items-center justify-center rounded-[40px] border-8 transition-all active:scale-95 ${
            isListening && activeMode === 'youtube' ? 'border-green-400 animate-pulse' : 'border-red-600 bg-red-700 shadow-lg'
          }`}
        >
          <Youtube size={80} />
          <span className="text-2xl font-black mt-2 uppercase text-center">YouTube</span>
        </button>

        {/* СВЯЗЬ (пустая пока) */}
        <button className="aspect-square flex flex-col items-center justify-center rounded-[40px] border-8 border-slate-800 bg-slate-800/50 opacity-30">
          <Phone size={60} />
          <span className="text-2xl font-bold mt-2 uppercase">Связь</span>
        </button>

      </div>
    </main>
  );
}