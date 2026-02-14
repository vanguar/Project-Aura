"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Film, Heart, Settings, Youtube, ArrowLeft, Bell, BellOff, Bot, Stethoscope, Mic, MicOff, Trash2, Send, Languages } from 'lucide-react';

export default function AuraHome() {
  const [view, setView] = useState<'home' | 'meds' | 'ai'>('home');
  const [isListening, setIsListening] = useState(false);
  const [activeMode, setActiveMode] = useState<'movie' | 'youtube' | null>(null);
  const [statusText, setStatusText] = useState("AURA готова");
  const [heardText, setHeardText] = useState("");
  const [serverIp, setServerIp] = useState("127.0.0.1");
  const [medsSchedule, setMedsSchedule] = useState("");
  const [remindersActive, setRemindersActive] = useState(false);

  // AI Chat state
  const [aiMessages, setAiMessages] = useState<Array<{role: string, content: string}>>([]);
  const [aiMode, setAiMode] = useState<'normal' | 'doctor' | 'translator'>('normal');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiListening, setAiListening] = useState(false);
  const [textInput, setTextInput] = useState("");
  // Используем строку вместо булевого значения, чтобы знать, КАКОЙ режим включается
 const [modeSwitching, setModeSwitching] = useState<string | null>(null);
  const [translatorWho, setTranslatorWho] = useState<'doctor' | 'mama'>('doctor');
  // Черновик переводчика: текст после голоса, до отправки
  const [translatorDraft, setTranslatorDraft] = useState("");
  const [translatorDraftWho, setTranslatorDraftWho] = useState<'doctor' | 'mama'>('doctor');

  const recognitionRef = useRef<any>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);
    return () => { if (recognitionRef.current) recognitionRef.current.stop(); };
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [aiMessages, aiLoading]);

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
      alert("Помилка зв'язку. Перевірте IP в налаштуваннях.");
    }
  };

  const handleBack = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.abort();
    }
    setIsListening(false);
    setAiListening(false);
    setView('home');
  };

  const startVoice = (mode: 'movie' | 'youtube') => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = 'uk-UA';

    recognition.onstart = () => { setIsListening(true); setActiveMode(mode); setHeardText(""); };

    recognition.onresult = async (event: any) => {
      const text = event.results[0][0].transcript;
      setHeardText(text);
      const q = text.toLowerCase().replace(/(включи|запусти|знайди|фільм|ютуб|youtube)/g, "").trim();

      if (mode === 'movie') {
        setStatusText(`Шукаю: ${q}...`);
        try {
          const res = await fetch(`http://${serverIp}:8000/search-movie?query=${encodeURIComponent(q)}`);
          const data = await res.json();
          setStatusText(data.found ? `✅ Грає: ${data.filename}` : "❌ Не знайдено");
        } catch (err) { setStatusText("❌ Помилка сервера"); }
      } else {
        window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`, "_blank");
      }
      setIsListening(false);
    };

    recognition.onend = () => { setIsListening(false); setActiveMode(null); };
    recognition.start();
  };

  // ============================================================
  // AI CHAT FUNCTIONS
  // ============================================================

  const openAiChat = async () => {
    try {
      const res = await fetch(`http://${serverIp}:8000/ai-chat/history`);
      const data = await res.json();
      setAiMode(data.mode);
      setAiMessages(data.messages.map((m: any) => ({
        role: m.role === 'model' ? 'assistant' : 'user',
        content: m.content
      })));
    } catch (e) {
      setAiMessages([]);
    }
    setView('ai');
  };

  const sendAiMessage = async (text: string) => {
    if (!text.trim() || aiLoading) return;

    const userMsg = text.trim();
    setTextInput("");
    setAiMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setAiLoading(true);

    try {
      const res = await fetch(`http://${serverIp}:8000/ai-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await res.json();
      setAiMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      if (data.notified) {
        setAiMessages(prev => [...prev, { role: 'system', content: '📨 Синові надіслано повідомлення' }]);
      }
    } catch (e) {
      setAiMessages(prev => [...prev, { role: 'assistant', content: '❌ Помилка зв\'язку з сервером' }]);
    }
    setAiLoading(false);
  };

  const startAiVoice = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Браузер не підтримує розпізнавання мови"); return; }
    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = aiMode === 'doctor' ? 'de-DE' : 'uk-UA';
    recognition.continuous = false;

    recognition.onstart = () => setAiListening(true);

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript;
      sendAiMessage(text);
      setAiListening(false);
    };

    recognition.onerror = () => setAiListening(false);
    recognition.onend = () => setAiListening(false);
    recognition.start();
  };

  const toggleDoctorMode = async () => {
    setModeSwitching('doctor');
    try {
      if (aiMode === 'normal') {
        const res = await fetch(`http://${serverIp}:8000/ai-chat/doctor-mode`, { method: 'POST' });
        const data = await res.json();
        setAiMode('doctor');
        setAiMessages([{ role: 'assistant', content: data.message }]);
      } else {
        // Повертаємо нормальний режим — сервер генерує резюме лікаря для мами
        const res = await fetch(`http://${serverIp}:8000/ai-chat/normal-mode`, { method: 'POST' });
        const data = await res.json();
        setAiMode('normal');
        setAiMessages([
          { role: 'system', content: '✅ Візит лікаря завершено. Звіт надіслано синові.' },
          { role: 'assistant', content: data.message }
        ]);
      }
    } catch (e) {
      alert("Помилка зв'язку з сервером");
    }
    setModeSwitching(null);
  };

  const clearAiHistory = async () => {
    try {
      await fetch(`http://${serverIp}:8000/ai-chat/clear`, { method: 'POST' });
      setAiMessages([]);
      setAiMode('normal');
    } catch (e) {
      alert("Помилка очищення");
    }
  };

  // ============================================================
  // TRANSLATOR FUNCTIONS
  // ============================================================

  const startTranslator = async () => {
    setModeSwitching('translator');
    try {
      await fetch(`http://${serverIp}:8000/translator/start`, { method: 'POST' });
      setAiMode('translator');
      setAiMessages([{
        role: 'system',
        content: '🔄 Режим перекладача увімкнено.\n🩺 Натисніть синю кнопку — говорить ЛІКАР (🇩🇪)\n👩 Натисніть жовту кнопку — говорить МАМА (🇺🇦)'
      }]);
    } catch (e) {
      alert("Помилка зв'язку з сервером");
    }
    setModeSwitching(null);
  };

  const stopTranslator = async () => {
    setModeSwitching('stop');
    try {
      await fetch(`http://${serverIp}:8000/translator/stop`, { method: 'POST' });
      setAiMode('normal');
      setAiMessages([{
        role: 'system',
        content: '✅ Сеанс перекладу завершено. Звіт надіслано синові.'
      }]);
    } catch (e) {
      alert("Помилка зв'язку з сервером");
    }
    setModeSwitching(null);
  };

  const sendTranslatorMessage = async (text: string, who: 'doctor' | 'mama') => {
    if (!text.trim() || aiLoading) return;
    setTextInput("");
    setAiLoading(true);

    const label = who === 'doctor' ? '🩺 Arzt' : '👩 Мама';
    setAiMessages(prev => [...prev, { role: 'user', content: `${label}: ${text}` }]);

    try {
      const res = await fetch(`http://${serverIp}:8000/translator/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, who })
      });
      const data = await res.json();
      const transLabel = who === 'doctor' ? '🇺🇦 Переклад для мами' : '🇩🇪 Übersetzung für den Arzt';
      setAiMessages(prev => [...prev, { role: 'assistant', content: `${transLabel}: ${data.translation}` }]);
    } catch (e) {
      setAiMessages(prev => [...prev, { role: 'assistant', content: '❌ Помилка перекладу' }]);
    }
    setAiLoading(false);
  };

  const startTranslatorVoice = (who: 'doctor' | 'mama', append: boolean = false) => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Браузер не підтримує розпізнавання мови"); return; }
    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = who === 'doctor' ? 'de-DE' : 'uk-UA';
    recognition.continuous = false;

    recognition.onstart = () => { setAiListening(true); setTranslatorWho(who); };

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript;
      if (append) {
        setTranslatorDraft(prev => (prev + ' ' + text).trim());
      } else {
        setTranslatorDraft(text);
        setTranslatorDraftWho(who);
      }
      setAiListening(false);
    };

    recognition.onerror = () => setAiListening(false);
    recognition.onend = () => setAiListening(false);
    recognition.start();
  };

  const sendTranslatorDraft = () => {
    if (!translatorDraft.trim() || aiLoading) return;
    sendTranslatorMessage(translatorDraft.trim(), translatorDraftWho);
    setTranslatorDraft("");
  };

  // ============================================================
  // AI CHAT VIEW
  // ============================================================
  if (view === 'ai') {
    return (
      <main className="h-screen w-full bg-slate-950 text-white flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-3 bg-slate-900 border-b border-slate-800">
          <button onClick={handleBack} className="p-2">
            <ArrowLeft size={28} />
          </button>
          <div className="text-center">
            <h2 className="text-xl font-black flex items-center gap-2">
              {aiMode === 'translator' ? (
                <><Languages size={24} /> ПЕРЕКЛАДАЧ</>
              ) : aiMode === 'doctor' ? (
                <><Stethoscope size={24} /> ARZT-MODUS</>
              ) : (
                <><Bot size={24} /> AI-ПОМІЧНИК</>
              )}
            </h2>
            <p className="text-xs opacity-60">
              {aiMode === 'translator' ? '🇩🇪 Deutsch ↔ Українська 🇺🇦' : aiMode === 'doctor' ? 'Deutsch · Medizinisch' : 'Українська · Галина Іванівна'}
            </p>
          </div>
          <button onClick={clearAiHistory} className="p-2">
            <Trash2 size={24} />
          </button>
        </div>

        {/* Mode toggle buttons */}
        <div className="mx-3 mt-2 flex gap-2">
          {aiMode === 'translator' ? (
            <button
              onClick={stopTranslator}
              disabled={modeSwitching !== null}
              className={`flex-1 py-3 rounded-2xl border-2 flex items-center justify-center gap-2 text-base font-black active:scale-95 bg-orange-600 border-orange-400 text-white ${modeSwitching ? 'opacity-50' : ''}`}
            >
              {modeSwitching === 'stop' ? (
                <div className="flex items-center gap-2">
                  <svg width="28" height="28" viewBox="0 0 28 28" className="animate-spin" style={{animationDuration: '3s'}}>
                    <circle cx="14" cy="6" r="2.5" fill="white" opacity="0.9"/>
                    <circle cx="20" cy="10" r="2" fill="white" opacity="0.6"/>
                    <circle cx="20" cy="18" r="1.5" fill="white" opacity="0.4"/>
                    <circle cx="14" cy="22" r="1.5" fill="white" opacity="0.3"/>
                    <circle cx="8" cy="18" r="2" fill="white" opacity="0.5"/>
                    <circle cx="8" cy="10" r="2.5" fill="white" opacity="0.7"/>
                  </svg>
                  <span className="text-xs">🤔</span>
                </div>
              ) : <><ArrowLeft size={18} /> ЗАВЕРШИТИ ПЕРЕКЛАД</>}
            </button>
          ) : (
            <>
              <button
                onClick={toggleDoctorMode}
                disabled={modeSwitching !== null}
                className={`flex-1 py-3 rounded-2xl border-2 flex items-center justify-center gap-2 text-sm font-black active:scale-95 ${
                  modeSwitching === 'doctor' ? 'opacity-70' : ''
                } ${
                  aiMode === 'doctor'
                    ? 'bg-green-700 border-green-500 text-white'
                    : 'bg-green-600 border-green-400 text-white'
                }`}
              >
                {modeSwitching === 'doctor' ? (
                  <div className="flex items-center gap-2">
                    <svg width="28" height="28" viewBox="0 0 28 28" className="animate-spin" style={{animationDuration: '3s'}}>
                      <circle cx="14" cy="6" r="2.5" fill="white" opacity="0.9"/>
                      <circle cx="20" cy="10" r="2" fill="white" opacity="0.6"/>
                      <circle cx="20" cy="18" r="1.5" fill="white" opacity="0.4"/>
                      <circle cx="14" cy="22" r="1.5" fill="white" opacity="0.3"/>
                      <circle cx="8" cy="18" r="2" fill="white" opacity="0.5"/>
                      <circle cx="8" cy="10" r="2.5" fill="white" opacity="0.7"/>
                    </svg>
                    <span className="text-xs">🤔</span>
                  </div>
                ) : aiMode === 'doctor' ? (
                  <><ArrowLeft size={16} /> МАМА 🇺🇦</>
                ) : (
                  <><Stethoscope size={16} /> ЛІКАР 🇩🇪</>
                )}
              </button>
              {aiMode === 'normal' && (
                <button
                  onClick={startTranslator}
                  disabled={modeSwitching !== null}
                  className={`flex-1 py-3 rounded-2xl border-2 flex items-center justify-center gap-2 text-sm font-black active:scale-95 bg-orange-500 border-orange-400 text-white ${
                    modeSwitching === 'translator' ? 'opacity-70' : ''
                  }`}
                >
                  {modeSwitching === 'translator' ? (
                    <div className="flex items-center gap-2">
                      <svg width="28" height="28" viewBox="0 0 28 28" className="animate-spin" style={{animationDuration: '3s'}}>
                        <circle cx="14" cy="6" r="2.5" fill="white" opacity="0.9"/>
                        <circle cx="20" cy="10" r="2" fill="white" opacity="0.6"/>
                        <circle cx="20" cy="18" r="1.5" fill="white" opacity="0.4"/>
                        <circle cx="14" cy="22" r="1.5" fill="white" opacity="0.3"/>
                        <circle cx="8" cy="18" r="2" fill="white" opacity="0.5"/>
                        <circle cx="8" cy="10" r="2.5" fill="white" opacity="0.7"/>
                      </svg>
                      <span className="text-xs">🤔</span>
                    </div>
                  ) : (
                    <><Languages size={16} /> ПЕРЕКЛАДАЧ 🔄</>
                  )}
                </button>
              )}
            </>
          )}
        </div>

        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {aiMessages.length === 0 && (
            <div className="text-center text-slate-500 mt-10">
              <Bot size={64} className="mx-auto mb-4 opacity-30" />
              <p className="text-xl font-bold">
                {aiMode === 'doctor' ? 'Sprechen Sie mit mir' : 'Натисніть 🎙️ щоб почати розмову'}
              </p>
              <p className="text-sm mt-2 opacity-50">
                {aiMode === 'doctor' ? 'Ich kenne die vollständige Krankengeschichte' : 'Я знаю всю медичну історію та допоможу'}
              </p>
            </div>
          )}

          {aiMessages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'system' ? (
                <div className="bg-yellow-900/40 text-yellow-300 text-sm px-4 py-2 rounded-xl text-center w-full">
                  {msg.content}
                </div>
              ) : (
                <div className={`max-w-[85%] px-4 py-3 rounded-3xl text-lg leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-lg'
                    : 'bg-slate-800 text-slate-100 rounded-bl-lg border border-slate-700'
                }`}>
                  {msg.content}
                </div>
              )}
            </div>
          ))}

          {aiLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 px-6 py-4 rounded-3xl rounded-bl-lg border border-slate-700">
                <div className="flex gap-1.5">
                  <span className="w-3 h-3 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></span>
                  <span className="w-3 h-3 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></span>
                  <span className="w-3 h-3 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></span>
                </div>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input area */}
        <div className="p-2 bg-slate-900 border-t border-slate-800">
          {aiMode === 'translator' ? (
            /* TRANSLATOR: Two microphone buttons */
            <div className="flex flex-col gap-2">
              {translatorDraft ? (
                /* === ЧЕРНОВИК: показываем распознанный текст для проверки === */
                <div className="flex flex-col gap-2">
                  <div className={`px-3 py-1.5 rounded-xl text-xs font-bold text-center ${
                    translatorDraftWho === 'doctor' ? 'bg-blue-900/50 text-blue-300' : 'bg-yellow-900/50 text-yellow-300'
                  }`}>
                    {translatorDraftWho === 'doctor' ? '🩺 Лікар сказав:' : '👩 Мама сказала:'}
                  </div>
                  <textarea
                    value={translatorDraft}
                    onChange={(e) => setTranslatorDraft(e.target.value)}
                    rows={3}
                    className="w-full bg-slate-800 text-white text-lg px-4 py-3 rounded-2xl border-2 border-blue-500 outline-none resize-none"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => startTranslatorVoice(translatorDraftWho, true)}
                      disabled={aiLoading || aiListening}
                      className={`flex-1 py-3 rounded-2xl border-2 flex items-center justify-center gap-2 text-sm font-black active:scale-95 ${
                        aiListening ? 'bg-red-600 border-red-400 animate-pulse' : 'bg-slate-700 border-slate-600'
                      }`}
                    >
                      <Mic size={20} />
                      {aiListening ? '...' : '🎙️ ДОПИСАТИ'}
                    </button>
                    <button
                      onClick={() => setTranslatorDraft("")}
                      className="py-3 px-4 rounded-2xl border-2 border-red-800 bg-red-900/50 flex items-center justify-center active:scale-95"
                    >
                      <Trash2 size={20} className="text-red-400" />
                    </button>
                    <button
                      onClick={sendTranslatorDraft}
                      disabled={!translatorDraft.trim() || aiLoading}
                      className={`flex-1 py-3 rounded-2xl border-2 flex items-center justify-center gap-2 text-sm font-black active:scale-95 disabled:opacity-30 ${
                        translatorDraftWho === 'doctor' ? 'bg-blue-600 border-blue-400' : 'bg-yellow-500 border-yellow-400'
                      }`}
                    >
                      <Send size={20} />
                      НАДІСЛАТИ ➡️
                    </button>
                  </div>
                </div>
              ) : (
                /* === ОБЫЧНЫЙ РЕЖИМ: микрофоны + ручной ввод === */
                <>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={textInput}
                      onChange={(e) => setTextInput(e.target.value)}
                      placeholder="Або введіть текст вручну..."
                      className="flex-1 bg-slate-800 text-white text-base px-4 py-2 rounded-2xl border border-slate-700 outline-none focus:border-blue-500"
                    />
                    <button
                      onClick={() => { sendTranslatorMessage(textInput, 'doctor'); setTextInput(""); }}
                      disabled={!textInput.trim() || aiLoading}
                      className="bg-blue-600 px-3 py-2 rounded-2xl active:scale-95 disabled:opacity-30 text-xs font-bold"
                    >
                      🇩🇪
                    </button>
                    <button
                      onClick={() => { sendTranslatorMessage(textInput, 'mama'); setTextInput(""); }}
                      disabled={!textInput.trim() || aiLoading}
                      className="bg-yellow-600 px-3 py-2 rounded-2xl active:scale-95 disabled:opacity-30 text-xs font-bold"
                    >
                      🇺🇦
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => startTranslatorVoice('doctor')}
                      disabled={aiLoading}
                      className={`flex-1 py-4 rounded-2xl border-4 flex items-center justify-center gap-2 text-lg font-black active:scale-95 ${
                        aiListening && translatorWho === 'doctor'
                          ? 'bg-red-600 border-red-400 animate-pulse'
                          : 'bg-blue-600 border-blue-400'
                      }`}
                    >
                      {aiListening && translatorWho === 'doctor' ? <MicOff size={24} /> : <Mic size={24} />}
                      🩺 ARZT
                    </button>
                    <button
                      onClick={() => startTranslatorVoice('mama')}
                      disabled={aiLoading}
                      className={`flex-1 py-4 rounded-2xl border-4 flex items-center justify-center gap-2 text-lg font-black active:scale-95 ${
                        aiListening && translatorWho === 'mama'
                          ? 'bg-red-600 border-red-400 animate-pulse'
                          : 'bg-yellow-500 border-yellow-400'
                      }`}
                    >
                      {aiListening && translatorWho === 'mama' ? <MicOff size={24} /> : <Mic size={24} />}
                      👩 МАМА
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            /* NORMAL / DOCTOR: Standard input */
            <>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') sendAiMessage(textInput); }}
                  placeholder={aiMode === 'doctor' ? 'Nachricht eingeben...' : 'Написати повідомлення...'}
                  className="flex-1 bg-slate-800 text-white text-lg px-4 py-3 rounded-2xl border border-slate-700 outline-none focus:border-blue-500"
                />
                <button
                  onClick={() => sendAiMessage(textInput)}
                  disabled={!textInput.trim() || aiLoading}
                  className="bg-blue-600 p-3 rounded-2xl active:scale-95 disabled:opacity-30"
                >
                  <Send size={24} />
                </button>
              </div>
              <button
                onClick={startAiVoice}
                disabled={aiLoading}
                className={`w-full py-4 rounded-2xl border-4 flex items-center justify-center gap-3 text-2xl font-black uppercase active:scale-95 ${
                  aiListening
                    ? 'bg-red-600 border-red-400 animate-pulse'
                    : 'bg-blue-600 border-blue-400'
                }`}
              >
                {aiListening ? <MicOff size={32} /> : <Mic size={32} />}
                {aiListening 
                  ? (aiMode === 'doctor' ? 'HÖRE ZU...' : 'СЛУХАЮ...')
                  : (aiMode === 'doctor' ? 'SPRECHEN' : 'ГОВОРИТИ 🎙️')
                }
              </button>
            </>
          )}
        </div>
      </main>
    );
  }

  // ============================================================
  // MEDS VIEW
  // ============================================================
  if (view === 'meds') {
    return (
      <main className="h-screen w-full bg-slate-950 text-white p-2 flex flex-col gap-2 overflow-hidden">
        <div className="h-[20vh] flex gap-2">
          {!remindersActive ? (
            <button 
              onClick={async () => {
                await fetch(`http://${serverIp}:8000/enable-reminders`, {method: 'POST'});
                setRemindersActive(true);
                alert("ТЕСТ ЗАПУЩЕНО! Зачекайте 30 секунд.");
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
          <pre className="text-xl font-bold whitespace-pre-wrap leading-tight">{medsSchedule}</pre>
        </div>

        <button 
          onClick={handleBack}
          className="h-[10vh] bg-slate-800 rounded-3xl text-xl font-bold uppercase flex items-center justify-center gap-4 border border-slate-700"
        >
          <ArrowLeft size={32} /> Назад
        </button>
      </main>
    );
  }

  // ============================================================
  // HOME VIEW
  // ============================================================
  return (
    <main className="h-screen w-full bg-slate-950 text-white p-2 flex flex-col gap-2 overflow-hidden font-sans">
      <div className="h-[10vh] flex justify-between items-center px-4 bg-slate-900 rounded-3xl border border-slate-800 shadow-lg">
        <h1 className="text-3xl font-black text-blue-500 tracking-tighter uppercase">AURA</h1>
        <button onClick={saveIp} className="p-3 bg-slate-800 rounded-full border border-slate-700 active:bg-slate-700">
          <Settings size={28} />
        </button>
      </div>

      <div className="h-[12vh] bg-blue-900/20 border-l-4 border-blue-600 p-4 rounded-3xl flex flex-col justify-center">
        <p className="text-xl font-bold leading-tight">{statusText}</p>
        {heardText && <p className="text-green-400 italic">"{heardText}"</p>}
      </div>

      <div className="flex-1 flex flex-col gap-2">
        <button 
          onClick={() => startVoice('movie')} 
          className={`flex-[2] rounded-[40px] border-8 flex flex-col items-center justify-center active:scale-95 shadow-2xl ${
            isListening && activeMode === 'movie' ? 'bg-green-600 border-green-400 animate-pulse' : 'bg-blue-600 border-blue-500'
          }`}
        >
          <Film size={64} /><span className="text-3xl font-black mt-2 uppercase tracking-widest">ФІЛЬМИ</span>
        </button>

        <div className="flex-[2] flex gap-2">
          <button 
            onClick={openMeds} 
            className="flex-1 bg-green-600 rounded-[40px] border-8 border-green-400 flex flex-col items-center justify-center active:scale-95 shadow-2xl"
          >
            <Heart size={56} fill="white" /><span className="text-2xl font-black mt-1 uppercase tracking-widest">ЛІКИ</span>
          </button>

          <button 
            onClick={openAiChat} 
            className="flex-1 bg-purple-600 rounded-[40px] border-8 border-purple-400 flex flex-col items-center justify-center active:scale-95 shadow-2xl"
          >
            <Bot size={56} /><span className="text-2xl font-black mt-1 uppercase tracking-wide">AI</span>
            <span className="text-xs font-bold opacity-70 uppercase">помічник</span>
          </button>
        </div>

        <button 
          onClick={() => startVoice('youtube')}
          className={`flex-1 rounded-[30px] border-4 flex items-center justify-center gap-4 active:scale-95 shadow-lg ${
            isListening && activeMode === 'youtube' ? 'bg-green-600 border-green-400 animate-pulse' : 'bg-red-600 border-red-400'
          }`}
        >
          <Youtube size={40} /><span className="text-2xl font-black uppercase">YouTube</span>
        </button>
      </div>
    </main>
  );
}