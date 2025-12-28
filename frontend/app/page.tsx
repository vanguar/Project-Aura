"use client";

import React, { useState, useEffect } from 'react';
import { Film, Phone, Heart, Bell, Home, Settings } from 'lucide-react';

export default function AuraHome() {
  const [isListening, setIsListening] = useState(false);
  const [statusText, setStatusText] = useState("Нажмите 'Фильмы' или скажите 'Домой'");
  const [recognizedText, setRecognizedText] = useState("");
  
  // Состояние для IP-адреса телефона (мини-сервера)
  const [serverIp, setServerIp] = useState("127.0.0.1"); 

  // При загрузке пытаемся подтянуть сохраненный IP из памяти браузера
  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);
  }, []);

  const saveIp = () => {
    const ip = prompt("Введите IP-адрес мини-сервера (например, 192.168.1.15):", serverIp);
    if (ip) {
      setServerIp(ip);
      localStorage.setItem('aura_server_ip', ip);
    }
  };

  const playMovie = async (title: string) => {
    setStatusText(`Ищу: ${title}...`);
    try {
      // Запрос идет на конкретный IP телефона, а не на домен Vercel
      const response = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(title)}`);
      const data = await response.json();

      if (data.found) {
        setStatusText(`Играет: ${data.filename}`);
      } else {
        setStatusText("Фильм не найден в памяти телефона");
      }
    } catch (error) {
      setStatusText("Нет связи с телефоном! Проверьте IP.");
    }
    setIsListening(false);
  };

  const handleVoiceInput = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatusText("Браузер не поддерживает голос");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.onstart = () => {
      setIsListening(true);
      setStatusText("Слушаю вас...");
    };

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript.toLowerCase();
      setRecognizedText(text);
      
      if (text.includes("включи") || text.includes("запусти") || text.includes("найди")) {
        const movieTitle = text.replace(/(включи|запусти|найди|фильм)/g, "").strip();
        playMovie(movieTitle);
      } else if (text.includes("домой")) {
        window.location.reload();
      } else {
        setStatusText(`Не поняла команду: "${text}"`);
        setIsListening(false);
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
      setStatusText("Ошибка микрофона");
    };

    recognition.start();
  };

  return (
    <main className="fixed inset-0 bg-slate-950 text-slate-100 flex flex-col p-6 overflow-hidden font-sans">
      {/* Хедер с кнопкой настройки IP для тебя */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <div className="w-6 h-6 rounded-full bg-blue-600 animate-pulse"></div>
          <h1 className="text-4xl font-black tracking-tighter text-blue-500">AURA</h1>
        </div>
        <button onClick={saveIp} className="p-4 bg-slate-800 rounded-full text-slate-400">
          <Settings size={30} />
        </button>
      </div>

      {/* Статус-бар */}
      <div className="mb-12 bg-slate-900/50 border-l-8 border-blue-600 p-8 rounded-2xl">
        <p className="text-3xl font-medium text-slate-300 mb-2">Статус:</p>
        <p className="text-5xl font-bold text-white leading-tight">{statusText}</p>
      </div>

      {/* Сетка кнопок (минимум 1/4 экрана каждая) */}
      <div className="grid grid-cols-2 gap-8 flex-grow">
        <button 
          onClick={handleVoiceInput}
          className={`relative overflow-hidden aspect-square flex flex-col items-center justify-center rounded-[50px] border-8 transition-all active:scale-95 ${
            isListening 
              ? 'border-green-400 bg-green-900/30 animate-pulse' 
              : 'border-blue-500 bg-blue-600 shadow-[0_0_50px_rgba(37,99,235,0.4)]'
          }`}
        >
          <Film size={140} strokeWidth={1.5} />
          <span className="text-5xl font-black mt-6 tracking-widest uppercase">Фильмы</span>
        </button>

        <button className="aspect-square flex flex-col items-center justify-center rounded-[50px] border-8 border-slate-800 bg-slate-800/50 opacity-50">
          <Phone size={120} />
          <span className="text-4xl font-bold mt-6 uppercase">Связь</span>
        </button>

        <button className="aspect-square flex flex-col items-center justify-center rounded-[50px] border-8 border-slate-800 bg-slate-800/50 opacity-50">
          <Heart size={120} />
          <span className="text-4xl font-bold mt-6 uppercase">Здоровье</span>
        </button>

        <button className="aspect-square flex flex-col items-center justify-center rounded-[50px] border-8 border-slate-800 bg-slate-800/50 opacity-50">
          <Bell size={120} />
          <span className="text-4xl font-bold mt-6 uppercase">Утилиты</span>
        </button>
      </div>
    </main>
  );
}