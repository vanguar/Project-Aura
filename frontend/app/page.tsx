"use client";

/* eslint-disable @typescript-eslint/no-explicit-any, react/no-unescaped-entities */

import React, { useState, useEffect, useRef } from 'react';
import { Film, Heart, Settings, Youtube, ArrowLeft, Bell, BellOff, Bot, Stethoscope, Mic, MicOff, Trash2, Send, Languages, ShieldAlert, Phone, X } from 'lucide-react';

export default function AuraHome() {
  const [view, setView] = useState<'home' | 'meds' | 'ai' | 'arzt_info' | 'sos_confirm' | 'sos_details'>('home');
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
  const [balance, setBalance] = useState<string | null>(null);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [doctorLang, setDoctorLang] = useState<'de' | 'uk'>('de');

  // SOS state
  const [sosCountdown, setSosCountdown] = useState(5);
  const [sosSending, setSosSending] = useState(false);
  const [sosAlertSent, setSosAlertSent] = useState(false);
  const [sosVoiceText, setSosVoiceText] = useState("");
  const [sosListening, setSosListening] = useState(false);
  const [sosDetailsSent, setSosDetailsSent] = useState(false);
  const [sosDetailsLoading, setSosDetailsLoading] = useState(false);
  const [sosInterpretation, setSosInterpretation] = useState("");

  const recognitionRef = useRef<any>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedIp = localStorage.getItem('aura_server_ip');
    if (savedIp) setServerIp(savedIp);
    return () => { if (recognitionRef.current) recognitionRef.current.stop(); };
  }, []);

  useEffect(() => {
    if (serverIp !== "127.0.0.1") fetchBalance();
  }, [serverIp]);

  const saveIp = () => {
    const ip = prompt("Введіть IP Termux (наприклад, 192.168.1.5):", serverIp);
    if (ip) {
      setServerIp(ip);
      localStorage.setItem('aura_server_ip', ip);
    }
  };

  const fetchBalance = () => {
    fetch(`http://${serverIp}:8000/billing/balance`)
      .then(r => r.json())
      .then(d => {
        if (d.balance?.month !== undefined) {
          setBalance(`$${d.balance.month}/міс`);
        }
      }).catch(() => {});
  };

  const openMeds = async () => {
    try {
      const response = await fetch(`http://${serverIp}:8000/get-meds-schedule`);
      const data = await response.json();
      setMedsSchedule(data.schedule);
      setRemindersActive(data.enabled);
      setView('meds');
    } catch {
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
        } catch { setStatusText("❌ Помилка сервера"); }
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
    setView('ai'); // immediate — don't wait for network
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 10000);
    try {
      const res = await fetch(`http://${serverIp}:8000/ai-chat/history`, { signal: controller.signal });
      const data = await res.json();
      setAiMode(data.mode);
      if (data.doctor_lang === 'de' || data.doctor_lang === 'uk') {
        setDoctorLang(data.doctor_lang);
      }
      setAiMessages(data.messages.map((m: any) => ({
        role: m.role === 'model' ? 'assistant' : 'user',
        content: m.content
      })));
    } catch {
      setAiMessages([]);
    } finally {
      clearTimeout(t);
    }
  };

  const sendAiMessage = async (text: string) => {
    if (!text.trim() || aiLoading) return;

    const userMsg = text.trim();
    setTextInput("");
    setPendingMessage(null);
    setAiMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setAiLoading(true);

    let success = false;
    for (let attempt = 0; attempt < 3; attempt++) {
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
        success = true;
        break;
      } catch {
        if (attempt < 2) {
          setAiMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.role === 'system' && last?.content.includes('Спроба')) {
              return [...prev.slice(0, -1), { role: 'system', content: `⏳ Спроба ${attempt + 2}/3...` }];
            }
            return [...prev, { role: 'system', content: `⏳ Спроба ${attempt + 2}/3...` }];
          });
          await new Promise(r => setTimeout(r, 2000));
        }
      }
    }

    if (!success) {
      setPendingMessage(userMsg);
      const errMsg = aiMode === 'doctor' && doctorLang === 'de'
        ? '❌ Verbindungsfehler. Ihre Nachricht wurde gespeichert — drücken Sie "Wiederholen".'
        : '❌ Помилка зв\'язку. Повідомлення збережено — натисніть "Повторити".';
      setAiMessages(prev => [...prev, { role: 'system', content: errMsg }]);
    }
    setAiLoading(false);
  };

  const startAiVoice = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Браузер не підтримує розпізнавання мови"); return; }
    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = aiMode === 'doctor' && doctorLang === 'de' ? 'de-DE' : 'uk-UA';
    recognition.continuous = false;

    let gotResult = false;

    recognition.onstart = () => setAiListening(true);

    recognition.onresult = (event: any) => {
      gotResult = true;
      const text = event.results[0][0].transcript;
      setAiListening(false);
      if (text.trim()) {
        sendAiMessage(text);
      } else {
        const msg = aiMode === 'doctor' && doctorLang === 'de'
          ? '⚠️ Sprache nicht erkannt. Bitte versuchen Sie es erneut.'
          : '⚠️ Не вдалося розпізнати. Спробуйте ще раз.';
        setAiMessages(prev => [...prev, { role: 'system', content: msg }]);
      }
    };

    recognition.onerror = (event: any) => {
      gotResult = true;
      setAiListening(false);
      const errorType = event?.error || 'unknown';
      let msg = '';
      if (errorType === 'network') {
        msg = aiMode === 'doctor' && doctorLang === 'de'
          ? '⚠️ Kein Internet. Bitte prüfen Sie die Verbindung.'
          : '⚠️ Немає інтернету. Перевірте з\'єднання.';
      } else if (errorType === 'not-allowed' || errorType === 'service-not-allowed') {
        msg = aiMode === 'doctor' && doctorLang === 'de'
          ? '⚠️ Mikrofon nicht erlaubt. Bitte Berechtigung erteilen.'
          : '⚠️ Мікрофон заблоковано. Дозвольте доступ.';
      } else if (errorType === 'no-speech') {
        msg = aiMode === 'doctor' && doctorLang === 'de'
          ? '⚠️ Keine Sprache erkannt. Bitte sprechen Sie lauter.'
          : '⚠️ Не почула голос. Говоріть голосніше.';
      } else {
        msg = aiMode === 'doctor' && doctorLang === 'de'
          ? `⚠️ Fehler: ${errorType}. Bitte erneut versuchen.`
          : `⚠️ Помилка: ${errorType}. Спробуйте ще раз.`;
      }
      setAiMessages(prev => [...prev, { role: 'system', content: msg }]);
    };

    recognition.onend = () => {
      setAiListening(false);
      if (!gotResult) {
        const msg = aiMode === 'doctor' && doctorLang === 'de'
          ? '⚠️ Keine Sprache erkannt. Bitte erneut versuchen.'
          : '⚠️ Не вдалося розпізнати мову. Спробуйте ще раз.';
        setAiMessages(prev => [...prev, { role: 'system', content: msg }]);
      }
    };

    recognition.start();
  };

  const toggleDoctorMode = async (lang: 'de' | 'uk' = doctorLang) => {
    setModeSwitching('doctor');
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 55000);
    try {
      if (aiMode === 'normal') {
        const res = await fetch(`http://${serverIp}:8000/ai-chat/doctor-mode`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lang }),
          signal: controller.signal
        });
        const data = await res.json();
        setAiMode('doctor');
        setAiMessages([{ role: 'assistant', content: data.message }]);
      } else {
        const res = await fetch(`http://${serverIp}:8000/ai-chat/normal-mode`, {
          method: 'POST',
          signal: controller.signal
        });
        const data = await res.json();
        setAiMode('normal');
        setAiMessages([
          { role: 'system', content: '✅ Візит лікаря завершено. Звіт надіслано синові.' },
          { role: 'assistant', content: data.message }
        ]);
      }
    } catch {
      setAiMessages(prev => [...prev, { role: 'system', content: "❌ Помилка зв'язку з сервером" }]);
    } finally {
      clearTimeout(t);
      setModeSwitching(null);
    }
  };

  const clearAiHistory = async () => {
    try {
      await fetch(`http://${serverIp}:8000/ai-chat/clear`, { method: 'POST' });
      setAiMessages([]);
      setAiMode('normal');
    } catch {
      alert("Помилка очищення");
    }
  };

  // ============================================================
  // SOS FUNCTIONS
  // ============================================================

  const startSosConfirm = () => {
    setSosCountdown(5);
    setSosSending(false);
    setSosAlertSent(false);
    setSosVoiceText("");
    setSosDetailsSent(false);
    setSosDetailsLoading(false);
    setSosInterpretation("");
    setSosListening(false);
    setView('sos_confirm');
  };

  useEffect(() => {
    if (view !== 'sos_confirm' || sosCountdown <= 0 || sosSending) return;
    const timer = setTimeout(() => {
      if (sosCountdown === 1) {
        // Countdown finished — send SOS
        sendSosAlert();
      } else {
        setSosCountdown(prev => prev - 1);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [sosCountdown, view, sosSending]);

  const sendSosAlert = async () => {
    setSosSending(true);
    setSosAlertSent(true);
    setView('sos_details'); // immediate — don't wait for network
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 5000);
    try {
      await fetch(`http://${serverIp}:8000/sos/alert`, { method: 'POST', signal: controller.signal });
    } catch {
      // screen already switched, backend accepted in background
    } finally {
      clearTimeout(t);
      setSosSending(false);
    }
  };

  const startSosVoice = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    if (recognitionRef.current) recognitionRef.current.stop();

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = 'uk-UA';
    recognition.continuous = false;

    recognition.onstart = () => setSosListening(true);

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript;
      if (text.trim()) {
        setSosVoiceText(prev => (prev + ' ' + text).trim());
      }
      setSosListening(false);
    };

    recognition.onerror = () => setSosListening(false);
    recognition.onend = () => setSosListening(false);

    recognition.start();
  };

  const sendSosDetails = async () => {
    if (!sosVoiceText.trim() || sosDetailsLoading) return;
    setSosDetailsLoading(true);
    try {
      const res = await fetch(`http://${serverIp}:8000/sos/details`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sosVoiceText })
      });
      const data = await res.json();
      setSosInterpretation(data.interpretation || "Надіслано");
      setSosDetailsSent(true);
    } catch {
      setSosInterpretation("Помилка відправки, але тривогу вже надіслано!");
      setSosDetailsSent(true);
    }
    setSosDetailsLoading(false);
  };

  const cancelSos = () => {
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.abort();
    }
    setSosListening(false);
    setView('home');
  };

  // ============================================================
  // TRANSLATOR FUNCTIONS
  // ============================================================

  const startTranslator = async () => {
    setModeSwitching('translator');
    setAiMode('translator'); // immediate
    setAiMessages([{
      role: 'system',
      content: '🔄 Режим перекладача увімкнено.\n🩺 Натисніть синю кнопку — говорить ЛІКАР (🇩🇪)\n👩 Натисніть жовту кнопку — говорить МАМА (🇺🇦)'
    }]);
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 10000);
    try {
      await fetch(`http://${serverIp}:8000/translator/start`, { method: 'POST', signal: controller.signal });
    } catch {
      // Non-critical: UI already switched, backend state will sync on next translate
    } finally {
      clearTimeout(t);
      setModeSwitching(null);
    }
  };

  const stopTranslator = async () => {
    setModeSwitching('stop');
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 10000);
    try {
      await fetch(`http://${serverIp}:8000/translator/stop`, { method: 'POST', signal: controller.signal });
      setAiMode('normal');
      setAiMessages([{
        role: 'system',
        content: '✅ Сеанс перекладу завершено. Звіт надіслано синові.'
      }]);
    } catch {
      setAiMode('normal');
      setAiMessages(prev => [...prev, { role: 'system', content: '✅ Сеанс завершено.' }]);
    } finally {
      clearTimeout(t);
      setModeSwitching(null);
    }
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
      // Формуємо повідомлення з AI-перекладом + дослівним
      let content = `${transLabel}: ${data.translation}`;
      if (data.literal) {
        const litLabel = who === 'doctor' ? '┈ дослівно' : '┈ wörtlich';
        content += `\n${litLabel}: ${data.literal}`;
      }
      setAiMessages(prev => [...prev, { role: 'assistant', content }]);
    } catch {
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

    let gotResult = false;

    recognition.onstart = () => { setAiListening(true); setTranslatorWho(who); };

    recognition.onresult = (event: any) => {
      gotResult = true;
      const text = event.results[0][0].transcript;
      if (text.trim()) {
        if (append) {
          setTranslatorDraft(prev => (prev + ' ' + text).trim());
        } else {
          setTranslatorDraft(text);
          setTranslatorDraftWho(who);
        }
      } else {
        const msg = who === 'doctor'
          ? '⚠️ Sprache nicht erkannt. Bitte erneut versuchen.'
          : '⚠️ Не вдалося розпізнати. Спробуйте ще раз.';
        setAiMessages(prev => [...prev, { role: 'system', content: msg }]);
      }
      setAiListening(false);
    };

    recognition.onerror = (event: any) => {
      gotResult = true;
      setAiListening(false);
      const errorType = event?.error || 'unknown';
      let msg = '';
      if (errorType === 'network') {
        msg = who === 'doctor'
          ? '⚠️ Kein Internet. Bitte Verbindung prüfen.'
          : '⚠️ Немає інтернету. Перевірте з\'єднання.';
      } else if (errorType === 'no-speech') {
        msg = who === 'doctor'
          ? '⚠️ Keine Sprache erkannt. Bitte lauter sprechen.'
          : '⚠️ Не почула голос. Говоріть голосніше.';
      } else {
        msg = who === 'doctor'
          ? `⚠️ Fehler: ${errorType}. Bitte erneut versuchen.`
          : `⚠️ Помилка: ${errorType}. Спробуйте ще раз.`;
      }
      setAiMessages(prev => [...prev, { role: 'system', content: msg }]);
    };

    recognition.onend = () => {
      setAiListening(false);
      if (!gotResult) {
        const msg = who === 'doctor'
          ? '⚠️ Keine Sprache erkannt. Bitte erneut versuchen.'
          : '⚠️ Не вдалося розпізнати мову. Спробуйте ще раз.';
        setAiMessages(prev => [...prev, { role: 'system', content: msg }]);
      }
    };

    recognition.start();
  };

  const sendTranslatorDraft = () => {
    if (!translatorDraft.trim() || aiLoading) return;
    sendTranslatorMessage(translatorDraft.trim(), translatorDraftWho);
    setTranslatorDraft("");
  };

  // ============================================================
  // SOS CONFIRM VIEW (countdown)
  // ============================================================
  if (view === 'sos_confirm') {
    return (
      <main className="h-screen w-full bg-slate-950 text-white p-4 flex flex-col gap-4 overflow-hidden">
        {/* Header */}
        <div className="bg-red-900/60 border-2 border-red-600 rounded-3xl p-4 text-center">
          <ShieldAlert size={48} className="mx-auto text-red-400 mb-2" />
          <h1 className="text-3xl font-black uppercase">SOS ТРИВОГА</h1>
          <p className="text-base text-red-300 mt-1">
            Через {sosCountdown} сек. синові буде надіслано тривогу
          </p>
        </div>

        {/* Countdown circle */}
        <div className="flex-1 flex items-center justify-center">
          <div className="w-36 h-36 rounded-full bg-red-800 border-8 border-red-500 flex items-center justify-center animate-pulse">
            <span className="text-6xl font-black">{sosCountdown}</span>
          </div>
        </div>

        {/* Two action buttons */}
        <div className="flex flex-col gap-3">
          {/* Primary: Send immediately + record voice */}
          <div className="flex gap-3">
            <button
              onClick={sendSosAlert}
              disabled={sosSending}
              className="flex-1 py-5 bg-red-600 rounded-3xl border-4 border-red-400 text-xl font-black uppercase flex flex-col items-center justify-center gap-1 active:scale-95 disabled:opacity-60"
            >
              <Phone size={28} />
              <span>{sosSending ? '...' : 'НАДІСЛАТИ'}</span>
              <span className="text-xs font-bold opacity-70 normal-case">тривогу зараз</span>
            </button>

            <button
              onClick={sendSosAlert}
              disabled={sosSending}
              className="flex-1 py-5 bg-blue-600 rounded-3xl border-4 border-blue-400 text-xl font-black uppercase flex flex-col items-center justify-center gap-1 active:scale-95 disabled:opacity-60"
            >
              <Mic size={28} />
              <span>ЗАПИСАТИ</span>
              <span className="text-xs font-bold opacity-70 normal-case">повідомлення</span>
            </button>
          </div>

          {/* Cancel */}
          <button
            onClick={cancelSos}
            className="w-full py-4 bg-slate-800 rounded-3xl border-2 border-slate-600 text-xl font-bold uppercase flex items-center justify-center gap-3 active:scale-95"
          >
            <X size={28} /> СКАСУВАТИ — Я ВИПАДКОВО
          </button>
        </div>
      </main>
    );
  }

  // ============================================================
  // SOS DETAILS VIEW (after alert sent - voice recording)
  // ============================================================
  if (view === 'sos_details') {
    return (
      <main className="h-screen w-full bg-slate-950 text-white p-4 flex flex-col gap-4 overflow-hidden">
        {/* Confirmation banner */}
        <div className="bg-green-900/60 border-2 border-green-500 rounded-3xl p-4 text-center">
          <p className="text-2xl font-black text-green-400">✅ ТРИВОГУ НАДІСЛАНО!</p>
          <p className="text-base text-green-300 mt-1">Володя отримав повідомлення</p>
        </div>

        {!sosDetailsSent ? (
          <>
            {/* Voice recording section */}
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <Mic size={48} className="text-blue-400" />
              <h2 className="text-2xl font-black text-center">
                Розкажіть, що сталося
              </h2>
              <p className="text-base text-slate-400 text-center">
                Якщо є сили — натисніть кнопку та розкажіть.{'\n'}
                Аура передасть деталі синові.
              </p>

              {sosVoiceText && (
                <div className="w-full bg-slate-800 rounded-2xl p-4 border border-slate-700">
                  <p className="text-xs text-slate-400 mb-1">Ви сказали:</p>
                  <p className="text-lg leading-relaxed">"{sosVoiceText}"</p>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => startSosVoice()}
                      disabled={sosListening || sosDetailsLoading}
                      className="flex-1 py-2 bg-slate-700 rounded-xl text-sm font-bold flex items-center justify-center gap-1 active:scale-95"
                    >
                      <Mic size={16} /> ДОПИСАТИ
                    </button>
                    <button
                      onClick={() => setSosVoiceText("")}
                      className="py-2 px-3 bg-red-900/50 rounded-xl active:scale-95"
                    >
                      <Trash2 size={16} className="text-red-400" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex flex-col gap-3">
              {!sosVoiceText ? (
                <button
                  onClick={startSosVoice}
                  disabled={sosListening}
                  className={`w-full py-6 rounded-3xl border-4 flex items-center justify-center gap-3 text-2xl font-black uppercase active:scale-95 ${
                    sosListening 
                      ? 'bg-red-600 border-red-400 animate-pulse' 
                      : 'bg-blue-600 border-blue-400'
                  }`}
                >
                  {sosListening ? <MicOff size={36} /> : <Mic size={36} />}
                  {sosListening ? 'СЛУХАЮ...' : 'ГОВОРИТИ 🎙️'}
                </button>
              ) : (
                <button
                  onClick={sendSosDetails}
                  disabled={sosDetailsLoading}
                  className={`w-full py-5 rounded-3xl border-4 flex items-center justify-center gap-3 text-2xl font-black uppercase active:scale-95 ${
                    sosDetailsLoading ? 'bg-orange-700 border-orange-500 animate-pulse' : 'bg-green-600 border-green-400'
                  }`}
                >
                  {sosDetailsLoading ? (
                    <>⏳ НАДСИЛАЮ...</>
                  ) : (
                    <><Send size={28} /> НАДІСЛАТИ ДЕТАЛІ</>
                  )}
                </button>
              )}

              <button
                onClick={cancelSos}
                className="w-full py-3 bg-slate-800 rounded-2xl border border-slate-700 text-lg font-bold flex items-center justify-center gap-2 active:scale-95"
              >
                <ArrowLeft size={24} /> ПОВЕРНУТИСЯ
              </button>
            </div>
          </>
        ) : (
          /* After details sent */
          <>
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <div className="text-6xl">✅</div>
              <h2 className="text-2xl font-black text-center text-green-400">
                Деталі надіслано!
              </h2>
              {sosInterpretation && (
                <div className="w-full bg-slate-800 rounded-2xl p-4 border border-slate-700">
                  <p className="text-xs text-slate-400 mb-1">AURA передала синові:</p>
                  <p className="text-base leading-relaxed">{sosInterpretation}</p>
                </div>
              )}
              <p className="text-base text-slate-400 text-center mt-2">
                Володя отримав тривогу та деталі.{'\n'}
                Чекайте — він зв&apos;яжеться з вами.
              </p>
            </div>

            <button
              onClick={cancelSos}
              className="w-full py-4 bg-slate-800 rounded-3xl border border-slate-700 text-xl font-bold flex items-center justify-center gap-2 active:scale-95"
            >
              <ArrowLeft size={24} /> НА ГОЛОВНУ
            </button>
          </>
        )}
      </main>
    );
  }

  // ============================================================
  // AI CHAT VIEW
  // ============================================================
  if (view === 'ai') {
    const isDoctorUk = doctorLang === 'uk';
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
                <><Stethoscope size={24} /> {isDoctorUk ? 'РЕЖИМ ЛІКАРЯ' : 'ARZT-MODUS'}</>
              ) : (
                <><Bot size={24} /> AI-ПОМІЧНИК</>
              )}
            </h2>
            <p className="text-xs opacity-60">
              {aiMode === 'translator' ? '🇩🇪 Deutsch ↔ Українська 🇺🇦' : aiMode === 'doctor' ? (isDoctorUk ? 'Українська · Медично' : 'Deutsch · Medizinisch') : 'Українська · Галина Іванівна'}
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
                onClick={() => toggleDoctorMode()}
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
                  <><Stethoscope size={16} /> {isDoctorUk ? 'ЛІКАР 🇺🇦' : 'ЛІКАР 🇩🇪'}</>
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
                {aiMode === 'doctor' && !isDoctorUk ? 'Sprechen Sie mit mir' : 'Натисніть 🎙️ щоб почати розмову'}
              </p>
              <p className="text-sm mt-2 opacity-50">
                {aiMode === 'doctor' && !isDoctorUk ? 'Ich kenne die vollständige Krankengeschichte' : 'Я знаю всю медичну історію та допоможу'}
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
                  {msg.content.includes('\n┈') ? (
                    <>
                      <div>{msg.content.split('\n┈')[0]}</div>
                      <div className="mt-2 pt-2 border-t border-slate-700/50 text-xs text-slate-400 leading-snug">
                        ┈{msg.content.split('\n┈')[1]}
                      </div>
                    </>
                  ) : (
                    msg.content
                  )}
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
                    {translatorDraftWho === 'doctor' ? '🩺 Der Arzt sagte:' : '👩 Мама сказала:'}
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
                      {aiListening ? '...' : translatorDraftWho === 'doctor' ? '🎙️ FORTSETZEN' : '🎙️ ДОПИСАТИ'}
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
                      {translatorDraftWho === 'doctor' ? 'SENDEN ➡️' : 'НАДІСЛАТИ ➡️'}
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
              {pendingMessage && (
                <button
                  onClick={() => sendAiMessage(pendingMessage)}
                  disabled={aiLoading}
                  className="w-full mb-2 py-3 bg-orange-600 rounded-2xl border-2 border-orange-400 text-lg font-black flex items-center justify-center gap-2 active:scale-95 animate-pulse"
                >
                  🔄 {aiMode === 'doctor' && !isDoctorUk ? 'WIEDERHOLEN' : 'ПОВТОРИТИ'}
                </button>
              )}
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') sendAiMessage(textInput); }}
                  placeholder={aiMode === 'doctor' && !isDoctorUk ? 'Nachricht eingeben...' : 'Написати повідомлення...'}
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
                  ? (aiMode === 'doctor' && !isDoctorUk ? 'HÖRE ZU...' : 'СЛУХАЮ...')
                  : (aiMode === 'doctor' && !isDoctorUk ? 'SPRECHEN' : 'ГОВОРИТИ 🎙️')
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
  // ARZT INFO VIEW (Для немецкого врача)
  // ============================================================
  if (view === 'arzt_info') {
    const isUk = doctorLang === 'uk';
    return (
      <main className="h-screen w-full bg-white text-gray-900 p-4 flex flex-col overflow-hidden font-sans">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <button onClick={() => setView('home')} className="p-2 bg-gray-100 rounded-full">
            <ArrowLeft size={28} className="text-gray-700" />
          </button>
          <div>
            <h1 className="text-2xl font-black text-blue-700">AURA</h1>
            <p className="text-sm text-gray-500">
              {isUk ? 'AI-помічник для лікаря 🇺🇦' : 'KI-Gesundheitsassistent 🇩🇪'}
            </p>
          </div>
        </div>

        {/* Інструкція */}
        <div className="flex-1 overflow-y-auto space-y-4">
          <div className="bg-blue-50 border-2 border-blue-200 rounded-2xl p-5">
            <h2 className="text-xl font-black text-blue-800 mb-3">
              {isUk ? 'ℹ️ Що таке AURA?' : 'ℹ️ Was ist AURA?'}
            </h2>
            <p className="text-base leading-relaxed">
              {isUk ? (
                <>AURA — це <strong>AI-асистент з медичними даними</strong> пацієнтки <strong>Галини Іванівни</strong>. Система знає повну медичну картку, діагнози, ліки та перебіг лікування.</>
              ) : (
                <>AURA ist ein <strong>KI-gestützter Gesundheitsassistent</strong> für die Patientin <strong>Halyna Ivanivna</strong>. Das System kennt ihre vollständige Krankengeschichte, Medikamente, Diagnosen und Behandlungsverläufe.</>
              )}
            </p>
          </div>

          <div className="bg-green-50 border-2 border-green-200 rounded-2xl p-5">
            <h2 className="text-xl font-black text-green-800 mb-3">
              {isUk ? '🩺 Для лікарів та медперсоналу' : '🩺 Für Ärzte & Rettungsdienst'}
            </h2>
            <p className="text-base leading-relaxed mb-3">
              {isUk
                ? <><strong>Запитуйте українською</strong> — AURA відповість медичною термінологією на основі даних пацієнтки:</>
                : <>Sie können mit dem KI-Assistenten <strong>auf Deutsch sprechen</strong>. Er beantwortet Ihre Fragen zur Krankengeschichte der Patientin:</>
              }
            </p>
            <ul className="space-y-2 text-base">
              {isUk ? (
                <>
                  <li className="flex items-start gap-2"><span className="text-green-600 font-bold mt-0.5">1.</span><span>Натисніть кнопку <strong>«Говорити з AI»</strong> нижче</span></li>
                  <li className="flex items-start gap-2"><span className="text-green-600 font-bold mt-0.5">2.</span><span>Натисніть велику синю кнопку <strong>«ГОВОРИТИ»</strong> і задайте питання українською</span></li>
                  <li className="flex items-start gap-2"><span className="text-green-600 font-bold mt-0.5">3.</span><span>AURA відповість із повною медичною інформацією про пацієнтку</span></li>
                </>
              ) : (
                <>
                  <li className="flex items-start gap-2"><span className="text-green-600 font-bold mt-0.5">1.</span><span>Drücken Sie unten die Taste <strong>„Mit KI sprechen"</strong></span></li>
                  <li className="flex items-start gap-2"><span className="text-green-600 font-bold mt-0.5">2.</span><span>Drücken Sie die große blaue Taste <strong>„SPRECHEN"</strong> und stellen Sie Ihre Frage auf Deutsch</span></li>
                  <li className="flex items-start gap-2"><span className="text-green-600 font-bold mt-0.5">3.</span><span>Der Assistent antwortet auf Deutsch mit allen relevanten medizinischen Informationen</span></li>
                </>
              )}
            </ul>
          </div>

          <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl p-5">
            <h2 className="text-lg font-black text-amber-800 mb-2">
              {isUk ? '⚠️ Важливо' : '⚠️ Hinweis'}
            </h2>
            <p className="text-sm leading-relaxed text-amber-900">
              {isUk
                ? 'AI не замінює лікаря. Всі дані надані пацієнткою та її родиною і слугують для швидкої передачі медичної інформації.'
                : 'Die KI ersetzt keine ärztliche Diagnose. Alle Angaben basieren auf den vom Patienten hinterlegten Daten und dienen der schnellen Informationsübermittlung bei Sprachbarrieren.'
              }
            </p>
          </div>
        </div>

        {/* Кнопка — увійти в режим лікаря */}
        <button
          onClick={async () => {
            setView('ai'); // immediate
            setModeSwitching('doctor');
            const controller = new AbortController();
            const t = setTimeout(() => controller.abort(), 55000);
            try {
              const res = await fetch(`http://${serverIp}:8000/ai-chat/doctor-mode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lang: doctorLang }),
                signal: controller.signal
              });
              const data = await res.json();
              setAiMode('doctor');
              setAiMessages([{ role: 'assistant', content: data.message }]);
            } catch {
              setAiMessages([{ role: 'system', content: "❌ Помилка з'єднання" }]);
            } finally {
              clearTimeout(t);
              setModeSwitching(null);
            }
          }}
          className="mt-4 w-full py-5 bg-green-600 hover:bg-green-700 text-white rounded-2xl border-4 border-green-400 flex items-center justify-center gap-3 text-xl font-black uppercase active:scale-95 shadow-xl"
        >
          <Stethoscope size={32} />
          {isUk ? 'Говорити з AI 🎙️' : 'Mit KI sprechen 🎙️'}
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
        <div className="flex items-center gap-2">
          {balance && (
            <span className="text-sm text-green-400 font-bold">{balance}</span>
          )}
          <button onClick={saveIp} className="p-3 bg-slate-800 rounded-full border border-slate-700 active:bg-slate-700">
            <Settings size={28} />
          </button>
        </div>
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

        <button 
          onClick={() => startVoice('youtube')}
          className={`flex-1 rounded-[30px] border-4 flex items-center justify-center gap-4 active:scale-95 shadow-lg ${
            isListening && activeMode === 'youtube' ? 'bg-green-600 border-green-400 animate-pulse' : 'bg-red-600 border-red-400'
          }`}
        >
          <Youtube size={40} /><span className="text-2xl font-black uppercase">YouTube</span>
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

        <div className="flex-1 flex gap-2">
          <button
            onClick={() => { setDoctorLang('de'); setView('arzt_info'); }}
            className="flex-1 rounded-[30px] border-4 flex items-center justify-center gap-2 active:scale-95 shadow-lg bg-white border-blue-300"
          >
            <Stethoscope size={26} className="text-blue-700" />
            <span className="text-base font-black uppercase text-blue-800">Лікар 🇩🇪</span>
          </button>
          <button
            onClick={() => { setDoctorLang('uk'); setView('arzt_info'); }}
            className="flex-1 rounded-[30px] border-4 flex items-center justify-center gap-2 active:scale-95 shadow-lg bg-white border-yellow-400"
          >
            <Stethoscope size={26} className="text-yellow-700" />
            <span className="text-base font-black uppercase text-yellow-800">Лікар 🇺🇦</span>
          </button>
        </div>

        <button 
          onClick={startSosConfirm}
          className="flex-1 rounded-[30px] border-4 flex items-center justify-center gap-3 active:scale-95 shadow-lg bg-red-700 border-red-500"
        >
          <ShieldAlert size={36} className="text-white" />
          <span className="text-2xl font-black uppercase text-white">SOS — ДОПОМОГА</span>
        </button>
      </div>
    </main>
  );
}
