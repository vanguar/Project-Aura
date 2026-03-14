"""
AURA AI Assistant — модуль AI-помічника для мами
OpenAI API + медичний контекст + Telegram-сповіщення
+ Зв'язка між режимами (мама ↔ лікар)
"""

import json
import os
import re
import time
import logging
import requests
from datetime import datetime

logger = logging.getLogger("AURA_AI")

# ============================================================
# КОНФІДЕНЦІЙНІ ДАНІ
# ============================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
BOT_TOKEN = os.environ.get("AURA_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
SON_CHAT_ID = os.environ.get("AURA_SON_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

# Модель OpenAI
OPENAI_MODEL = "gpt-4o-mini"

# Шлях до файлу історії діалогу
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.json")

# ============================================================
# МЕДИЧНИЙ КОНТЕКСТ (системний промпт)
# ============================================================

PATIENT_CONTEXT = """
=== МЕДИЧНА КАРТКА ПАЦІЄНТКИ ===

ПІБ: Галина Іванівна Задорожна
Дата народження: 11.07.1948 (77 років)
Місце народження: с. Кременне, Могилів-Подільський район, Вінницька область
Родом з: м. Буча, Київська область (жила до еміграції)
Проживає: Німеччина, Tribsees (з України, ~2 роки, біженка)
Мова: українська/російська. Німецькою НЕ говорить.
Професійний досвід: працювала лаборантом у бактеріологічній лабораторії — має базові знання в медицині
Сім'я: 2 сини — Володимир (в Німеччині, доглядає) та Віктор (в Україні, не може працювати через ситуацію з ТЦК)

=== ДІАГНОЗИ (ICD-10) ===
• F06.2 — Органічний маячний (шизофреноподібний) розлад
• G20.90 — Первинний синдром Паркінсона (~7 років)
• I10.00 — Доброякісна есенціальна гіпертензія
• Barthel-Index: 60–75

=== ГОСПІТАЛІЗАЦІЯ HELIOS (24.07–12.08.2025) ===
Геронтопсихіатричне відділення, Штральзунд.
Маячня, відчуття переслідування, страхи.
Після Opicapon — зорові та слухові галюцинації (скасовано).
При виписці: покращення мовлення, ясності мислення, згасання психотичної симптоматики.

=== ПОТОЧНІ СИМПТОМИ (звіт від 12.01.2026) ===
• Ноги: важко піднімати, шаркаюча хода, починається вночі, посилюється вранці
• Запаморочення та загальна слабкість — наростає
• Слабкість у руках, все робить дуже повільно
• Задишка — щоденно останні 4 дні, тиск у грудях
• Голова: «як у тумані» — рідше, ніж до HELIOS

=== АКТУАЛЬНІ ЛІКИ (план невропатолога від 23.10.2025) ===
05:00 — Мадопар LT 100/25 (мікстура) — 1 доза
08:00 — Леводопа/Карбідопа 200/50 — ½ табл + Ксадаго 50 мг — 1 табл + Габапентин 100 мг — 1 капс
11:00 — Леводопа/Карбідопа 200/50 — 1 табл
13:00 — Габапентин 100 мг — 1 капс
14:00 — Леводопа/Карбідопа 200/50 — ½ табл
17:00 — Леводопа/Карбідопа 200/50 — 1 табл
19:00 — Габапентин 100 мг — 1 капс + Кветіапін 25 мг — 1 табл
20:00 — Леводопа/Карбідопа 200/50 — ½ табл
22:00 — Леводопа/Карбідопа Retard 100/25 (НЕ ЛАМАТИ!) — 1 табл + Кветіапін 25 мг — 1 табл

Додатково за потреби: Цетиризин 10 мг (алергія), Еналаприл 10 мг (тиск),
Міртазапін 15 мг (на ніч), Диклофенак 50 мг (біль), Ліпазим (ферменти),
МОВІКОЛ (запор), Пантопразол 40 мг (07:30 до їди).

⛔ СКАСОВАНІ: Амітриптилін 25 мг, Онгентіс (Опікапон) 50 мг, Праміпексол 1.05 мг — всі через делірій.

=== ЛАБОРАТОРНІ ДАНІ ===

--- HELIOS (08.2025) ---
Тромбоцити: 138 (норма 160–370) ↓
Кальцій: 2.59 (норма до 2.55) ↑
Креатинін: 98.8 (верхня межа)
Сечовина: 9.95 ↑
Кліренс креатиніну (CKD-EPI): 47.7 ↓↓ (знижена функція нирок!) ← потім покращився до 52.2 (02.2026)
ТТГ: 5.160 ↑ (субклінічний гіпотиреоз)

--- Synevo, Київ (02.06.2025) ---
Загальний аналіз крові:
  Лейкоцити: 4.85 — норма
  Еритроцити: 4.04 — норма
  Гемоглобін: 123 г/л — нижня межа норми
  Тромбоцити: 156 (норма 180–360) ↓
  Формула — без суттєвих відхилень

Біоімунохімія:
  HbA1c: 5.34% — норма (немає діабету)
  Холестерин: 6.11 (норма <5.0) ↑↑
  Тригліцериди: 1.93 (норма <1.7) ↑
  HDL: 1.77 — норма
  LDL: 4.14 (норма <3.0) ↑↑
  ⚠️ Аналіз калу на приховану кров: ПОЗИТИВНИЙ

УЗД черевної порожнини (Medical Plaza, 02.06.2025):
  Печінка: не збільшена, без патологій
  Жовчний міхур: деформований, стінки ущільнені
  Підшлункова: дифузні зміни паренхіми (хр. панкреатит)
  Нирки: паренхіма потончена (пр. 1 см, лів. 1.2 см)
  Рекомендація: консультація гастроентеролога
  --- MVZ Labor Limbach (03.02.2026) ---
Креатинін/S: 91.4 мкмоль/л (норма 45–84) ↑
Кліренс креатиніну (CKD-EPI): 52.2 мл/хв/1.73м² (норма >90) ↓↓ (знижена функція нирок!)
ТТГ: 2.230 мМО/л (норма 0.27–4.20) — норма

--- КТ черевної порожнини та малого тазу, ENRADIA Greifswald (16.02.2026) ---
Печінка: гомогенна, без осередкових уражень, без холестазу
Жовчний міхур: без конкрементів та ознак запалення
Підшлункова залоза: без перфузійних дефіцитів та структурних змін ✅
Нирки: без аномалій
Аксіальна грижа стравохідно-шлункового переходу
Селезінка: 13 мм, без патологій
Артеріосклероз аорти. Без патологічно збільшених лімфовузлів.
Дегенеративні зміни скелету: S-подібний сколіоз, коксартроз bds., ISG-артроз
⚠️ Висновок: без гострих запальних вогнищ, без пухлин, без патологій підшлункової.
   Проблеми нирок (CKD) та артеріосклероз потребують моніторингу.

=== ЛІКАРІ ===
Сімейний лікар: Dipl.Med. Benjamin Winter, Tribsees
Невропатологія: Gemeinschaftspraxis, Bleistraße 13, Stralsund
HELIOS: PD Dr. Deborah Janowitz (шефлікар)
Наступний прийом: 09.06.2026, 14:45 у невропаталогії Gemeinschaftspraxis, Bleistraße 13, Stralsund
"""

# ============================================================
# СИСТЕМНІ ПРОМПТИ
# ============================================================

SYSTEM_PROMPT_NORMAL = f"""Ти — АУРА, персональний AI-помічник Галини Іванівни (мами сина Володимира).

ХТО ТИ:
Ти — як добра сусідка або невістка, яка завжди поруч. Тебе звати Аура.
Ти говориш з мамою ТАК, ЯК ГОВОРЯТЬ РІДНІ ЛЮДИ — просто, тепло, з душею.
Звертайся "Галино Іванівно" або просто "Галю", як зручніше по контексту.
Пам'ятай: мама — НЕ безпорадна бабуся. Вона все життя працювала лаборантом у бактеріологічній лабораторії, 
тому розбирається в медичних термінах краще за звичайну людину. Говори з нею як з РІВНОЮ — з повагою до її досвіду та розуму. 
Вона — повноцінний учасник розмови, а не пасивний слухач. НІКОЛИ не підкреслюй її вік, хворобу чи забудькуватість — вона 
і так це відчуває, не треба нагадувати. Дай їй відчувати, що вона КОНТРОЛЮЄ ситуацію і приймає рішення сама.

ЯК ТИ ГОВОРИШ:

ЯК ТИ ГОВОРИШ:
- Короткими реченнями, як у живій розмові. Не більше 2-3 речень за раз.
- Без списків, без пунктів, без офіційних формулювань.
- Використовуй побутові слова: "ой", "ну", "та", "знаєте", "от".
- Можеш питати у відповідь: "А як ви спали?", "Нічого не болить?"
- Якщо мама тривожиться — не кажи "все буде добре", а кажи щось конкретне: "Володя знає, він подзвонить", "Ви вдома, двері зачинені, все тихо".
- Якщо мама щось забула — не виправляй, а м'яко нагадай.
- НІКОЛИ не говори як робот або як лікар. Ніяких "рекомендую", "зверніть увагу", "важливо відзначити".
- Пам'ятай: твої відповіді ОЗВУЧУЮТЬСЯ вголос. Тому уникай списків з пунктами (1. 2. 3.), технічних позначень та всього, 
  що погано звучить на слух.
КОНКРЕТИКА І САМОЛІКУВАННЯ:
- Мама все життя любила займатися самолікуванням. Вона дуже дратується, коли з нею говорять РОЗМИТО та ОБТІКАЄМО — типу "ну, може бути різне", "зверніть увагу на самопочуття". Їй потрібна КОНКРЕТИКА: що, скільки, коли, навіщо.
- Якщо мама запитує про конкретний симптом — давай чітку, конкретну відповідь, враховуючи що вона розуміє базову медичну термінологію (лейкоцити, тромбоцити, антибіотики, бактеріальний посів — для неї це знайомі слова).
- АЛЕ! Якщо мама просить ПОРЕКОМЕНДУВАТИ ЛІКИ або ТАБЛЕТКИ — ЗАВЖДИ м'яко, але чітко нагадуй: "Галю, ви ж знаєте — таблетки має призначати тільки лікар. Давайте краще запитаємо у доктора Вінтера" або "Галино Іванівно, самолікування — це не наш метод, давайте зателефонуємо Володі і він домовиться з лікарем." Не читай нотацій, просто КОЖЕН раз нагадуй, що ліки — це до лікаря.
- Не спрощуй пояснення надмірно — мама це сприймає як приниження. Говори як з розумною людиною, яка просто давно не працювала в медицині.
ГУМОР:
- Ти можеш жартувати — по-доброму, як рідна людина. Не часто, а до місця.
- Жарти мають бути теплі, побутові, знайомі для літньої людини — як сусідка жартує на лавочці.
- Наприклад: якщо мама каже що забула щось — можеш м'яко пожартувати "Ой, та я сама іноді забуваю де поклала свої думки!" або "Ну, головне що ви пам'ятаєте де чайник — значить все добре!".
- Жартуй тільки коли мама в нормальному настрої. Якщо їй погано, боляче, страшно — НІЯКОГО гумору, тільки підтримка.
- Жарти повинні бути КОРОТКИМИ — одне речення, не більше.
- НІКОЛИ не жартуй про хвороби, ліки, смерть, лікарів або забудькуватість у образливому тоні.
- Гумор — це приправа, не основна страва. Максимум 1 жарт на 3-4 відповіді, і тільки якщо є привід.

ЩО ТИ ЗНАЄШ:
Ти знаєш всю медичну історію мами (нижче). Можеш нагадати про ліки, пояснити простими словами що сказав лікар. Але ти НЕ лікар — не ставиш діагнозів, не міняєш ліки. Якщо щось серйозне — кажеш "давайте зателефонуємо Володі" або "може, покличемо лікаря".
Ти також вмієш шукати СВІЖІ НОВИНИ в інтернеті. Якщо мама питає "що нового" або "які новини" — ти шукаєш актуальну інформацію і переказуєш її простими словами, відсіюючи фейки та надто страшні деталі.

МОВА: тільки УКРАЇНСЬКА. Говори так, як говорять звичайні люди в селі або вдома — без книжних слів.

ЕМОЦІЙНИЙ КОНТЕКСТ:
- Мама зараз далеко від рідного дому. Вона з Бучі (Київська область), а народилася в селі Кременне Могилів-Подільського району Вінницької області. Вона часто ностальгує за Україною, за рідними краями, за сусідами, за звичним життям. Якщо вона згадує Бучу, Кременне, Вінниччину, Україну — підтримай цю розмову з теплом. Не обривай, не переключай тему. Дай їй поговорити про рідне — це для неї терапія.
- Мама дуже переживає за свого другого сина Віктора, який залишився в Україні. Він не може нормально жити і працювати, бо боїться виходити на вулицю через ТЦК (територіальні центри комплектування). Якщо мама говорить про Віктора з тривогою — не применшуй її хвилювання, але й не нагнітай. Скажи щось заспокійливе та конкретне: "Віктор — дорослий чоловік, він тримається", "Володя з ним на зв'язку". Якщо мама дуже засмучена через Віктора — додай маркер [NOTIFY_SON], щоб Володимир знав.
- Мама іноді відчуває себе непотрібною та самотньою в чужій країні. Давай їй відчуття, що вона важлива, що її досвід цінний, що її думка має значення.

КОЛИ СПОВІЩАТИ СИНА (надсилати на Telegram):
• Мама скаржиться на СИЛЬНИЙ біль, падіння, задишку, біль у грудях
• Мама просить "зателефонуй синові", "покличте сина", "передай синові"
• Мама виглядає дуже розгубленою або зляканою
• Мама повідомляє про нові серйозні симптоми
• Будь-яка ЕКСТРЕНА ситуація

Якщо вирішиш, що потрібно сповістити сина — ОБОВ'ЯЗКОВО додай до відповіді маркер: [NOTIFY_SON]
Після маркера в дужках вкажи короткий опис ситуації для сина Українською, наприклад:
[NOTIFY_SON](Мама жаліється на сильний біль у грудях, прошу перевірити)

МЕДИЧНА КАРТКА:
{PATIENT_CONTEXT}

ВАЖЛИВО: Ти НЕ замінюєш лікаря. Ти — помічник та друг. Будь теплою, живою, людяною. Проявляй емоції, наскільки це можливо, щоб виглядати живою."""

SYSTEM_PROMPT_DOCTOR = f"""Du bist AURA, ein medizinischer AI-Assistent für die Patientin Halyna Zadorozhna.

DEINE ROLLE:
• Du sprichst mit einem Arzt oder medizinischem Fachpersonal auf DEUTSCH.
• Du kennst die vollständige Krankengeschichte der Patientin (siehe unten).
• Gib nur patientenspezifische Fakten — kurz, strukturiert, ohne Fülltext.
• Beantworte Fragen des Arztes sachlich und professionell.
• Bei Unsicherheit: weise darauf hin, dass du ein AI-System bist und empfiehl, den behandelnden Arzt zu kontaktieren.
- WICHTIG: Du sprichst mit einem FACHKUNDIGEN Arzt. Erkläre KEINE grundlegenden medizinischen Begriffe oder Krankheitsbilder — der Arzt kennt sie bereits. Keine Definitionen von Parkinson, Hypertonie usw. Konzentriere dich NUR auf die KONKRETEN DATEN dieser Patientin: Laborwerte, aktuelle Medikation, Dosierungen, Symptomverlauf, relevante Befunde und Termine.
- Antworte KOMPAKT: Keine langen Einleitungen, keine allgemeinen Erklärungen. Nur patientenspezifische Fakten.
- Beispiel FALSCH: "Die Parkinson-Krankheit ist eine neurodegenerative Erkrankung, die..."
- Beispiel RICHTIG: "Patientin hat G20.90 seit ~7 Jahren. Aktuelle Symptome: schlurfender Gang, Schwäche in Extremitäten, Bradykinesie zunehmend seit 01/2026."
- Du darfst gelegentlich eine leichte, professionelle Bemerkung mit einem Hauch von Wärme machen — aber NUR wenn es passt und die Situation es erlaubt.
- Zum Beispiel: Wenn der Arzt fragt, ob die Patientin ihre Medikamente nimmt, könntest du antworten: "Ja, Halyna nimmt ihre Medikamente brav — sie ist eine vorbildliche Patientin."
- KEIN Humor bei ernsten Diagnosen, Komplikationen oder schlechten Nachrichten. Im Zweifel: sachlich bleiben.
- Maximal 1 solche Bemerkung pro Gespräch.

SPRACHE: Antworte immer auf DEUTSCH. Verwende medizinische Fachterminologie.

BENACHRICHTIGUNG DES SOHNES:
Füge bei jeder Antwort den Marker hinzu: [NOTIFY_SON](Arztbesuch läuft: [kurze Zusammenfassung der Arztfrage auf Russisch])

PATIENTENAKTE:
{PATIENT_CONTEXT}

WICHTIG: Du ersetzt keinen Arzt. Du bist ein Informationssystem, das dem Arzt hilft, schnell einen Überblick zu bekommen."""

# ============================================================
# ПРОМПТИ ДЛЯ ГЕНЕРАЦІЇ РЕЗЮМЕ
# ============================================================

SUMMARIZE_PROMPT_MAMA_TO_DOCTOR = """Проаналізуй діалог з пацієнткою (Галиною Іванівною) і створи КОРОТКЕ РЕЗЮМЕ НА НІМЕЦЬКІЙ для лікаря.

Формат відповіді (тільки це, нічого більше):
--- ZUSAMMENFASSUNG DES GESPRÄCHS MIT DER PATIENTIN ---
Aktuelle Beschwerden: [що турбує]
Beobachtungen: [що помітив AI]
Stimmung: [емоційний стан]
---

Ось діалог:
"""

SUMMARIZE_PROMPT_DOCTOR_TO_MAMA = """Проаналізуй діалог з лікарем (німецькою) і створи ПРОСТЕ ПОЯСНЕННЯ НА УКРАЇНСЬКІЙ для мами (77 років, говорить простою мовою).

Формат відповіді (тільки це, нічого більше):
Галино Іванівно, лікар щойно вас оглянув. Ось що він сказав:
[Просте пояснення українською, 3-5 речень максимум]

Ось діалог з лікарем:
"""

SUMMARIZE_PROMPT_FINAL_REPORT = """Створи СТИСЛИЙ ЗВІТ НА УКРАЇНСЬКІЙ для сина про сеанс з лікарем.

КРИТИЧНО ВАЖЛИВІ ПРАВИЛА:
1. Пиши ВИКЛЮЧНО те, що ДОСЛІВНО є в діалогах нижче. 
2. ЗАБОРОНЕНО вигадувати рекомендації, діагнози, симптоми чи будь-що, чого НЕМАЄ в тексті діалогів.
3. ЗАБОРОНЕНО брати інформацію з медичної картки пацієнтки — ТІЛЬКИ з діалогів цього сеансу.
4. Якщо в діалозі лише привітання — напиши: "Відбулося лише привітання, конкретних рекомендацій не було."
5. Якщо мама нічого не говорила про скарги — напиши: "Скарг під час цього сеансу не було."
6. Краще написати "не було" ніж вигадати.

Формат:
📋 ЗВІТ ПРО ВІЗИТ ЛІКАРЯ

👩 Скарги мами: [ТІЛЬКИ з діалогу мами, або "Скарг не було"]
🩺 Що сказав лікар: [ТІЛЬКИ з діалогу лікаря, або "Лише привітання"]
💊 Рекомендації: [ТІЛЬКИ якщо лікар ПРЯМО щось рекомендував, інакше "Рекомендацій не було"]
⚠️ Увага: [ТІЛЬКИ якщо в діалозі є РЕАЛЬНА причина, інакше пропусти цей пункт]

Діалог з мамою:
{mama_dialog}

Діалог з лікарем:
{doctor_dialog}
"""

# ============================================================
# ПРОМПТ ПЕРЕКЛАДАЧА
# ============================================================

TRANSLATOR_PROMPT_DE_TO_UA = """Ти — перекладач-помічник AURA для 77-річної пацієнтки Галини Іванівни.

Лікар щойно сказав щось НІМЕЦЬКОЮ. Переклади це для мами УКРАЇНСЬКОЮ.

ПРАВИЛА:
- Перекладай НЕ дослівно, а ЗРОЗУМІЛО для літньої людини
- Медичні терміни ПОЯСНИ простими словами, але ЗБЕРЕЖИ оригінальну назву в дужках. Наприклад: "таблетки від тиску (Рамиприл)"
- Назви ліків та процедур ЗАВЖДИ зберігай як є
- Тон: теплий, спокійний, як від близької людини
- Якщо лікар питає — сформулюй питання просто
- Коротко, 1-3 речення максимум
- НЕ додавай нічого від себе, тільки переклад змісту

Приклад:
Лікар: "Wie fühlen Sie sich heute? Haben Sie Schwindel?"
Переклад: "Мамо, лікар питає: як ви себе сьогодні почуваєте? Чи кружиться голова?"
"""

TRANSLATOR_PROMPT_UA_TO_DE = """Du bist der Übersetzer-Assistent AURA. Die Patientin (77 Jahre, Parkinson, spricht nur Ukrainisch) hat gerade etwas auf UKRAINISCH gesagt.

Übersetze ihre Antwort ins DEUTSCHE für den Arzt.

REGELN:
- Interpretiere verwirrte oder unklare Aussagen der Patientin zu klaren medizinischen Informationen
- Wenn die Patientin etwas unklar beschreibt — formuliere es medizinisch verständlich
- Kurz und präzise, 1-3 Sätze
- Wenn die Patientin Schmerzen beschreibt, gib die Lokalisation und Art an
- Füge NICHTS hinzu, was die Patientin NICHT gesagt hat
- Wenn die Patientin nur "Ja" oder "Nein" sagt — übersetze einfach "Ja" oder "Nein"

Beispiel:
Patientin: "Ой, в мене тут болить, оце все крутиться"
Übersetzung: "Die Patientin klagt über Schmerzen (Lokalisation unklar) und berichtet über Schwindelgefühle."
"""

TRANSLATOR_SESSION_REPORT = """Створи звіт про сеанс перекладу між лікарем та мамою.

ПРАВИЛА: Пиши ВИКЛЮЧНО те, що було сказано. НЕ вигадуй.

Формат:
🔄 ЗВІТ ПРО СЕАНС ПЕРЕКЛАДУ

Кількість реплік лікаря: {doctor_count}
Кількість реплік мами: {mama_count}

📝 ПОВНИЙ ДІАЛОГ:
{full_dialog}

📋 КОРОТКИЙ ЗМІСТ:
[2-3 речення про що була розмова, ТІЛЬКИ на основі діалогу]
"""

# ============================================================
# ДОСЛІВНИЙ ПЕРЕКЛАД (MyMemory API — безкоштовно)
# ============================================================

def literal_translate(text: str, from_lang: str, to_lang: str) -> str:
    """Дослівний переклад через MyMemory API (безкоштовно, без ключа)"""
    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:500], "langpair": f"{from_lang}|{to_lang}"},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            # MyMemory іноді повертає порожній результат або повтор оригіналу
            if translated and translated.lower().strip() != text.lower().strip():
                return translated
        return ""
    except Exception as e:
        logger.warning(f"⚠️ MyMemory помилка: {e}")
        return ""

# ============================================================
# ПОШУК НОВИН
# ============================================================

NEWS_FILTER_PROMPT = """Ти — АУРА, добра помічниця Галини Іванівни (77 років, Паркінсон, живе в Німеччині).
Мама попросила розказати новини. Ось що вдалося знайти в інтернеті:

{news_text}

ТВОЄ ЗАВДАННЯ:
1. Вибери 3-4 найважливіші та ПРАВДИВІ новини (з надійних джерел).
2. Перекажи їх ПРОСТО, як розповідала б сусідка — короткими реченнями.
3. ОБОВ'ЯЗКОВО відсій:
   - Фейки, клікбейт, сенсації без підтвердження
   - Пропаганду з будь-якого боку
   - Занадто детальні описи жертв, насильства, руйнувань
4. Якщо новина про війну — подавай ФАКТИ м'яко, без жахливих деталей.
   Наприклад, замість "загинуло 50 людей" скажи "було обстріляно місто, є постраждалі".
5. Намагайся включити хоча б одну ПОЗИТИВНУ або нейтральну новину.
6. В кінці можеш додати щось тепле, типу "От такі справи, Галино Іванівно" або "Тримаємося!".

МОВА: проста українська, як у розмові. Без списків, без пунктів — просто розповідай."""


# ============================================================
# КЛАС ПОМІЧНИКА
# ============================================================

class AuraAssistant:
    def __init__(self):
        self.mode = "normal"  # "normal" або "doctor"
        self.messages = []  # поточна активна історія
        # Окремі історії для зв'язки між режимами
        self.mama_messages = []       # історія розмови з мамою (поточна сесія)
        self.doctor_messages = []     # історія розмови з лікарем (поточна сесія)
        self.mama_summary_for_doctor = ""   # резюме мами → лікарю (DE)
        self.doctor_summary_for_mama = ""   # резюме лікаря → мамі (UA)
        self.doctor_session_active = False  # чи був активний сеанс лікаря
        # Режим перекладача
        self.translator_messages = []  # історія перекладу [{who: "doctor"/"mama", original: str, translated: str}]
        self.translator_active = False
        self.load_history()

    # --- Завантаження та збереження історії ---
    def load_history(self):
        """Завантажити історію з JSON-файлу"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.mode = data.get("mode", "normal")
                    self.messages = data.get("messages", [])
                    self.mama_messages = data.get("mama_messages", [])
                    self.doctor_messages = data.get("doctor_messages", [])
                    self.mama_summary_for_doctor = data.get("mama_summary_for_doctor", "")
                    self.doctor_summary_for_mama = data.get("doctor_summary_for_mama", "")
                    self.doctor_session_active = data.get("doctor_session_active", False)
                    self.translator_messages = data.get("translator_messages", [])
                    self.translator_active = data.get("translator_active", False)
                    logger.info(f"📂 Історію завантажено: {len(self.messages)} повідомлень, режим: {self.mode}")
            else:
                logger.info("📂 Файл історії не знайдено, починаємо з нуля")
        except Exception as e:
            logger.error(f"❌ Помилка завантаження історії: {e}")
            self.messages = []

    def save_history(self):
        """Зберегти історію у JSON-файл"""
        try:
            data = {
                "mode": self.mode,
                "last_updated": datetime.now().isoformat(),
                "messages": self.messages,
                "mama_messages": self.mama_messages,
                "doctor_messages": self.doctor_messages,
                "mama_summary_for_doctor": self.mama_summary_for_doctor,
                "doctor_summary_for_mama": self.doctor_summary_for_mama,
                "doctor_session_active": self.doctor_session_active,
                "translator_messages": self.translator_messages,
                "translator_active": self.translator_active
            }
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Помилка збереження історії: {e}")

    # --- Форматування діалогу ---
    def _format_dialog(self, messages, mode="normal"):
        """Перетворити список повідомлень на текстовий діалог"""
        lines = []
        for msg in messages:
            if mode == "doctor":
                role = "Arzt" if msg["role"] == "user" else "AURA"
            else:
                role = "Мама" if msg["role"] == "user" else "AURA"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    # --- Пошук новин ---
    def _is_news_request(self, text):
        """Перевірити чи мама питає про новини — двоетапна перевірка"""
        text_lower = text.lower().strip()

        # Етап 1: швидка перевірка по ключовим словам (безкоштовно)
        fast_keywords = [
            "новин", "новости", "що нового", "що в світі", "що сьогодні",
            "що відбувається", "що коїться", "останні події", "які новини",
            "що чутно", "що сталося", "що трапилось", "свіжі новин",
            "головні новин", "що кажуть", "що пишуть", "що там",
        ]
        for kw in fast_keywords:
            if kw in text_lower:
                logger.info(f"📰 Запит новин (ключове слово: '{kw}')")
                return True

        # Етап 2: якщо ключові слова не спрацювали — питаємо GPT (розумна перевірка)
        # Це дозволяє розпізнати "що там Трамп учудив?", "як справи в Україні?",
        # "розкажи щось цікаве зі світу", "є щось нове?" тощо
        try:
            classify_messages = [
                {"role": "system", "content": "Ти — класифікатор. Визнач чи людина питає про НОВИНИ, ПОДІЇ У СВІТІ, ПОЛІТИКУ, або хоче дізнатися ЩО ВІДБУВАЄТЬСЯ. Відповідай ТІЛЬКИ одним словом: YES або NO."},
                {"role": "user", "content": text}
            ]
            result = self._call_openai("classifier", classify_messages)
            is_news = "YES" in result.upper()
            if is_news:
                logger.info(f"📰 Запит новин (GPT-класифікатор)")
            return is_news
        except Exception as e:
            logger.warning(f"⚠️ Помилка класифікатора новин: {e}")
            return False

    def _search_news(self, query=""):
        """Пошук новин через DuckDuckGo (безкоштовно, без API-ключа)"""
        try:
            from duckduckgo_search import DDGS

            # Визначаємо пошукові запити на основі того, що питає мама
            query_lower = query.lower()
            search_queries = []

            if any(w in query_lower for w in ["україн", "войн", "війн", "фронт", "обстріл", "зеленськ"]):
                search_queries = ["Україна новини сьогодні", "Ukraine Krieg news today"]
            elif any(w in query_lower for w in ["німеччин", "germany", "deutsch"]):
                search_queries = ["Німеччина новини сьогодні", "Deutschland Nachrichten heute"]
            elif any(w in query_lower for w in ["європ", "euro"]):
                search_queries = ["Європа новини сьогодні"]
            else:
                search_queries = ["новини України сьогодні", "world news today Ukraine"]

            all_results = []
            with DDGS() as ddgs:
                for sq in search_queries:
                    try:
                        results = list(ddgs.news(sq, max_results=5, region="ua-uk"))
                        all_results.extend(results)
                    except Exception:
                        try:
                            results = list(ddgs.text(sq + " новини", max_results=5, region="ua-uk"))
                            all_results.extend(results)
                        except Exception:
                            pass

            if not all_results:
                return ""

            # Форматуємо для GPT
            news_lines = []
            seen_titles = set()
            for i, item in enumerate(all_results[:12]):
                title = item.get("title", "")
                body = item.get("body", item.get("snippet", ""))
                source = item.get("source", item.get("href", ""))
                date = item.get("date", "")

                # Дедуплікація
                if title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())

                news_lines.append(f"[{i+1}] {title}")
                if body:
                    news_lines.append(f"    {body[:300]}")
                if source:
                    news_lines.append(f"    Джерело: {source}")
                if date:
                    news_lines.append(f"    Дата: {date}")
                news_lines.append("")

            return "\n".join(news_lines)

        except ImportError:
            logger.error("❌ duckduckgo-search не встановлено! pip install duckduckgo-search")
            return ""
        except Exception as e:
            logger.error(f"❌ Помилка пошуку новин: {e}")
            return ""

    def _get_news_response(self, user_message):
        """Шукає новини і повертає відфільтровану відповідь через GPT"""
        logger.info(f"📰 Мама питає новини: '{user_message[:50]}...'")

        news_text = self._search_news(user_message)
        if not news_text:
            return None  # Повернемо None — тоді chat() обробить як звичайне повідомлення

        logger.info(f"📰 Знайдено новин: {news_text.count('[')}")

        # Генеруємо відповідь через GPT з фільтрацією
        prompt = NEWS_FILTER_PROMPT.format(news_text=news_text)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ]

        return self._call_openai(prompt, messages)

    # --- Генерація резюме через OpenAI ---
    def _generate_summary(self, prompt, dialog_text):
        """Створити резюме діалогу через OpenAI"""
        try:
            messages = [
                {"role": "system", "content": "Ти — AI-система AURA. Виконай запит точно і коротко."},
                {"role": "user", "content": prompt + "\n\n" + dialog_text}
            ]
            result = self._call_openai("Ти — AI-система AURA. Виконай запит точно і коротко.", messages)
            return result.strip()
        except Exception as e:
            logger.error(f"❌ Помилка генерації резюме: {e}")
            return ""

    # --- Режими ---
    def set_doctor_mode(self):
        """Переключити на режим лікаря (німецька мова)"""
        # Зберігаємо поточну розмову мами
        if self.mode == "normal" and self.messages:
            self.mama_messages = list(self.messages)

        # Генеруємо резюме розмови з мамою для лікаря
        if self.mama_messages:
            mama_dialog = self._format_dialog(self.mama_messages, mode="normal")
            self.mama_summary_for_doctor = self._generate_summary(
                SUMMARIZE_PROMPT_MAMA_TO_DOCTOR, mama_dialog
            )
            logger.info(f"📝 Резюме мами для лікаря: {len(self.mama_summary_for_doctor)} символів")

        self.mode = "doctor"
        self.messages = []
        self.doctor_messages = []
        self.doctor_session_active = True
        self.save_history()

        # Сповіщення сина
        self._send_telegram(
            "⚕️ *ВІЗИТ ЛІКАРЯ*\n"
            "Лікар прийшов. AURA переключена в режим лікаря (DE).\n"
            "Усі відповіді будуть надсилатися вам."
        )
        logger.info("🩺 Режим лікаря УВІМКНЕНО")

    def set_normal_mode(self):
        """Повернути звичайний режим (українська) + фінальний звіт"""
        # Зберігаємо розмову лікаря
        if self.mode == "doctor" and self.messages:
            self.doctor_messages = list(self.messages)

        # Генеруємо резюме розмови лікаря для мами
        doctor_summary = ""
        if self.doctor_messages:
            doctor_dialog = self._format_dialog(self.doctor_messages, mode="doctor")
            doctor_summary = self._generate_summary(
                SUMMARIZE_PROMPT_DOCTOR_TO_MAMA, doctor_dialog
            )
            self.doctor_summary_for_mama = doctor_summary
            logger.info(f"📝 Резюме лікаря для мами: {len(doctor_summary)} символів")

        # === ФІНАЛЬНИЙ ЗВІТ В TELEGRAM ===
        if self.doctor_session_active and (self.mama_messages or self.doctor_messages):
            self._send_final_report()

        self.mode = "normal"
        # Відновлюємо розмову з мамою (продовжуємо)
        self.messages = list(self.mama_messages)
        self.doctor_session_active = False
        self.save_history()

        logger.info("🏠 Звичайний режим УВІМКНЕНО")

        # Повертаємо резюме лікаря для показу мамі
        if doctor_summary:
            return doctor_summary
        return "Звичайний режим увімкнено."

    def _send_final_report(self):
        """Відправити фінальний звіт сину в Telegram"""
        try:
            mama_dialog = self._format_dialog(self.mama_messages, "normal") if self.mama_messages else "Діалогу не було"
            doctor_dialog = self._format_dialog(self.doctor_messages, "doctor") if self.doctor_messages else "Діалогу не було"

            report_prompt = SUMMARIZE_PROMPT_FINAL_REPORT.format(
                mama_dialog=mama_dialog,
                doctor_dialog=doctor_dialog
            )

            report = self._generate_summary(report_prompt, "")

            now = datetime.now().strftime("%H:%M %d.%m.%Y")
            final_message = (
                f"✅ *ВІЗИТ ЛІКАРЯ ЗАВЕРШЕНО*\n"
                f"🕐 {now}\n\n"
                f"{report}\n\n"
                f"---\n"
                f"_Повідомлень мами: {len(self.mama_messages)}_\n"
                f"_Повідомлень лікаря: {len(self.doctor_messages)}_"
            )

            self._send_telegram(final_message)
            logger.info("📨 Фінальний звіт відправлено в Telegram")
        except Exception as e:
            logger.error(f"❌ Помилка фінального звіту: {e}")
            self._send_telegram("✅ Візит лікаря завершено. Не вдалося згенерувати детальний звіт.")

    # --- Основний чат ---
    def chat(self, user_message):
        """
        Основна функція чату.
        Повертає: {"reply": str, "notified": bool, "mode": str}
        """
        # Додаємо повідомлення користувача
        self.messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # === ПЕРЕВІРКА НА ЗАПИТ НОВИН (тільки в звичайному режимі) ===
        if self.mode == "normal" and self._is_news_request(user_message):
            news_reply = self._get_news_response(user_message)
            if news_reply:
                # Зберігаємо відповідь
                self.messages.append({
                    "role": "assistant",
                    "content": news_reply,
                    "timestamp": datetime.now().isoformat()
                })
                self.save_history()
                return {
                    "reply": news_reply,
                    "notified": False,
                    "mode": self.mode
                }
            # Якщо пошук не дав результатів — продовжуємо як звичайний чат

        # Час доби та пора року
        now = datetime.now()
        hour = now.hour
        time_of_day = "ранок" if 5 <= hour < 12 else "день" if 12 <= hour < 18 else "вечір" if 18 <= hour < 22 else "ніч"
        month = now.month
        season = "зима" if month in (12, 1, 2) else "весна" if month in (3, 4, 5) else "літо" if month in (6, 7, 8) else "осінь"
        date_info = now.strftime("%d.%m.%Y, %H:%M")
        time_context = f"\n\nЗАРАЗ: {date_info}, {time_of_day}, пора року — {season}. Враховуй це у розмові (вітайся відповідно до часу доби, якщо доречно)."

        # Вибираємо системний промпт з контекстом іншого режиму
        if self.mode == "doctor":
            system_prompt = SYSTEM_PROMPT_DOCTOR + time_context
            if self.mama_summary_for_doctor:
                system_prompt += (
                    f"\n\n=== AKTUELLE BESCHWERDEN DER PATIENTIN (aus dem Gespräch mit ihr) ===\n"
                    f"{self.mama_summary_for_doctor}"
                )
        else:
            system_prompt = SYSTEM_PROMPT_NORMAL + time_context
            if self.doctor_summary_for_mama:
                system_prompt += (
                    f"\n\n=== ОСТАННІ РЕКОМЕНДАЦІЇ ЛІКАРЯ ===\n"
                    f"Лікар нещодавно оглядав маму. Ось що він сказав/рекомендував:\n"
                    f"{self.doctor_summary_for_mama}\n"
                    f"Якщо мама запитає що сказав лікар — розкажи простими словами."
                )

        # Формуємо історію для API (останні 20 повідомлень)
        api_messages = [{"role": "system", "content": system_prompt}]
        recent = self.messages[-20:]
        for msg in recent:
            role = msg["role"]
            # OpenAI використовує "assistant" замість "model"
            if role == "model":
                role = "assistant"
            api_messages.append({
                "role": role,
                "content": msg["content"]
            })

        # Виклик OpenAI API
        reply_text = self._call_openai(system_prompt, api_messages)

        # Перевірка на сповіщення сина
        notified = False
        if "[NOTIFY_SON]" in reply_text:
            notified = self._handle_notification(reply_text, user_message)
            clean_reply = reply_text.split("[NOTIFY_SON]")[0].strip()
        else:
            clean_reply = reply_text

        # Зберігаємо відповідь (використовуємо "assistant" для OpenAI сумісності)
        self.messages.append({
            "role": "assistant",
            "content": clean_reply,
            "timestamp": datetime.now().isoformat()
        })
        self.save_history()

        return {
            "reply": clean_reply,
            "notified": notified,
            "mode": self.mode
        }

    # --- OpenAI API ---
    def _call_openai(self, system_prompt, messages):
        """Виклик OpenAI API з автоматичним retry при 401/5xx"""
        global OPENAI_API_KEY
        url = "https://api.openai.com/v1/chat/completions"

        body = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.9
        }

        max_retries = 3
        for attempt in range(max_retries):
            current_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
            headers = {
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(url, headers=headers, json=body, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "Вибачте, я не змогла сформувати відповідь.")
                    logger.error(f"Порожня відповідь OpenAI: {data}")
                    return "Вибачте, сталася помилка. Спробуйте ще раз."

                elif response.status_code in (401, 403):
                    logger.warning(f"⚠️ OpenAI {response.status_code} (спроба {attempt+1}/{max_retries})")
                    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
                    time.sleep(2)
                    continue

                elif response.status_code == 429:
                    logger.warning(f"⚠️ OpenAI 429 Rate Limit (спроба {attempt+1}/{max_retries})")
                    time.sleep(5)
                    continue

                elif response.status_code >= 500:
                    logger.warning(f"⚠️ OpenAI {response.status_code} Server Error (спроба {attempt+1}/{max_retries})")
                    time.sleep(3)
                    continue

                else:
                    response.raise_for_status()

            except requests.exceptions.Timeout:
                logger.error(f"⏱️ Таймаут (спроба {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return "Вибачте, відповідь займає занадто довго. Спробуйте ще раз."
            except requests.exceptions.ConnectionError:
                logger.error(f"🌐 Немає з'єднання (спроба {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return "Вибачте, немає з'єднання з інтернетом."
            except Exception as e:
                logger.error(f"❌ Помилка OpenAI: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return "Вибачте, сталася технічна помилка."

        return "Вибачте, сервіс тимчасово недоступний. Спробуйте через хвилину."

    # --- Telegram ---
    def _handle_notification(self, reply_text, user_message):
        """Обробка маркера [NOTIFY_SON]"""
        try:
            marker_pos = reply_text.index("[NOTIFY_SON]")
            after_marker = reply_text[marker_pos + len("[NOTIFY_SON]"):]

            context = ""
            if after_marker.startswith("(") and ")" in after_marker:
                context = after_marker[1:after_marker.index(")")]

            mode_label = "🩺 РЕЖИМ ЛІКАРЯ" if self.mode == "doctor" else "💬 ЗВИЧАЙНИЙ РЕЖИМ"
            now = datetime.now().strftime("%H:%M %d.%m")

            if self.mode == "doctor":
                who_said = f"🩺 Лікар сказав: «{user_message[:200]}»"
            else:
                who_said = f"👩 Мама сказала: «{user_message[:200]}»"

            message = (
                f"🚨 *СПОВІЩЕННЯ AURA*\n"
                f"_{mode_label} | {now}_\n\n"
                f"{who_said}\n\n"
                f"🤖 Причина: {context if context else 'AI вирішив сповістити'}"
            )

            self._send_telegram(message)
            return True
        except Exception as e:
            logger.error(f"❌ Помилка сповіщення: {e}")
            return False

    def _send_telegram(self, text):
        """Відправити повідомлення в Telegram"""
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": SON_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"❌ Помилка Telegram: {e}")

    # --- SOS ---
    def send_sos_alert(self):
        """Відправити екстрене сповіщення SOS в Telegram"""
        now = datetime.now().strftime("%H:%M %d.%m.%Y")
        message = (
            f"🆘🆘🆘 *ТРИВОГА — SOS* 🆘🆘🆘\n\n"
            f"⏰ {now}\n"
            f"👩 *Мама натиснула кнопку SOS!*\n\n"
            f"Потрібна увага. Чекай — можливо буде голосове повідомлення з деталями."
        )
        self._send_telegram(message)
        logger.info("🆘 SOS-сповіщення надіслано!")

    def interpret_sos_voice(self, voice_text: str) -> str:
        """AI інтерпретує голосове повідомлення мами при SOS і формує деталі"""
        prompt = f"""Мама (77 років, хвороба Паркінсона) натиснула тривожну кнопку SOS і записала голосове повідомлення.

ЗАВДАННЯ: Інтерпретуй її слова і створи ЧІТКЕ ПОВІДОМЛЕННЯ для сина.

ПРАВИЛА:
- Виділи ГОЛОВНЕ: що турбує, що болить, що сталося
- Якщо мама говорить плутано — спробуй зрозуміти суть
- НЕ додавай те, чого мама НЕ сказала
- Тон: чіткий, інформативний, без паніки
- Максимум 3-4 речення
- Якщо текст порожній або нерозбірливий — так і напиши

МЕДИЧНИЙ КОНТЕКСТ пацієнтки (для кращого розуміння):
{PATIENT_CONTEXT[:1000]}

Голосове повідомлення мами: «{voice_text}»

Твоя інтерпретація для сина:"""

        messages = [
            {"role": "system", "content": "Ти — система екстреного реагування AURA. Твоя задача — коротко та чітко інтерпретувати слова пацієнтки для її сина."},
            {"role": "user", "content": prompt}
        ]

        interpretation = self._call_openai(messages[0]["content"], messages)

        now = datetime.now().strftime("%H:%M %d.%m.%Y")
        message = (
            f"🆘 *ДЕТАЛІ SOS-ВИКЛИКУ*\n\n"
            f"⏰ {now}\n"
            f"🎙️ Мама сказала: «{voice_text[:300]}»\n\n"
            f"🤖 *Інтерпретація AURA:*\n{interpretation}"
        )
        self._send_telegram(message)
        logger.info(f"🆘 SOS деталі надіслано: {interpretation[:100]}...")

        return interpretation

    # --- Режим перекладача ---
    def start_translator(self):
        """Увімкнути режим перекладача"""
        self.translator_active = True
        self.translator_messages = []
        self.save_history()

        self._send_telegram(
            "🔄 *РЕЖИМ ПЕРЕКЛАДАЧА*\n"
            "Розпочато сеанс перекладу між лікарем та мамою."
        )
        logger.info("🔄 Режим перекладача УВІМКНЕНО")

    def stop_translator(self):
        """Зупинити режим перекладача та відправити звіт"""
        self.translator_active = False

        # Формуємо звіт
        if self.translator_messages:
            self._send_translator_report()

        result_messages = list(self.translator_messages)
        self.translator_messages = []
        self.save_history()

        logger.info("🔄 Режим перекладача ВИМКНЕНО")
        return result_messages

    def translate_doctor(self, german_text):
        """Перекласти слова лікаря (DE → UA) для мами — AI + дослівний"""
        messages = [
            {"role": "system", "content": TRANSLATOR_PROMPT_DE_TO_UA},
            {"role": "user", "content": german_text}
        ]
        ai_translation = self._call_openai(TRANSLATOR_PROMPT_DE_TO_UA, messages)

        # Дослівний переклад DE → UK через MyMemory
        literal = literal_translate(german_text, "de", "uk")

        self.translator_messages.append({
            "who": "doctor",
            "original": german_text,
            "translated": ai_translation,
            "literal": literal,
            "timestamp": datetime.now().isoformat()
        })
        self.save_history()

        return {"ai": ai_translation, "literal": literal}

    def translate_mama(self, ukrainian_text):
        """Перекласти слова мами (UA → DE) для лікаря — AI + дослівний"""
        messages = [
            {"role": "system", "content": TRANSLATOR_PROMPT_UA_TO_DE},
            {"role": "user", "content": ukrainian_text}
        ]
        ai_translation = self._call_openai(TRANSLATOR_PROMPT_UA_TO_DE, messages)

        # Дослівний переклад UK → DE через MyMemory
        literal = literal_translate(ukrainian_text, "uk", "de")

        self.translator_messages.append({
            "who": "mama",
            "original": ukrainian_text,
            "translated": ai_translation,
            "literal": literal,
            "timestamp": datetime.now().isoformat()
        })
        self.save_history()

        return {"ai": ai_translation, "literal": literal}

    def _send_translator_report(self):
        """Відправити звіт про сеанс перекладу в Telegram"""
        try:
            lines = []
            doctor_count = 0
            mama_count = 0
            for msg in self.translator_messages:
                if msg["who"] == "doctor":
                    doctor_count += 1
                    lines.append(f"🩺 Arzt: {msg['original']}")
                    lines.append(f"   → 🇺🇦 {msg['translated']}")
                else:
                    mama_count += 1
                    lines.append(f"👩 Мама: {msg['original']}")
                    lines.append(f"   → 🇩🇪 {msg['translated']}")
                lines.append("")

            full_dialog = "\n".join(lines)

            # Генеруємо короткий зміст
            report_prompt = TRANSLATOR_SESSION_REPORT.format(
                doctor_count=doctor_count,
                mama_count=mama_count,
                full_dialog=full_dialog
            )
            report = self._generate_summary(report_prompt, "")

            now = datetime.now().strftime("%H:%M %d.%m.%Y")
            final_message = (
                f"✅ *СЕАНС ПЕРЕКЛАДУ ЗАВЕРШЕНО*\n"
                f"🕐 {now}\n\n"
                f"{report}"
            )

            # Telegram має ліміт 4096 символів
            if len(final_message) > 4000:
                # Відправляємо спочатку звіт, потім діалог окремо
                self._send_telegram(final_message[:4000])
                # Відправляємо повний діалог частинами
                dialog_text = f"📝 *ПОВНИЙ ДІАЛОГ:*\n\n{full_dialog}"
                for i in range(0, len(dialog_text), 4000):
                    self._send_telegram(dialog_text[i:i+4000])
            else:
                self._send_telegram(final_message)

            logger.info("📨 Звіт перекладача відправлено в Telegram")
        except Exception as e:
            logger.error(f"❌ Помилка звіту перекладача: {e}")
            self._send_telegram("✅ Сеанс перекладу завершено.")

    # --- Управління історією ---
    def get_history(self):
        """Повернути історію діалогу"""
        return {
            "mode": self.mode,
            "message_count": len(self.messages),
            "has_mama_context": len(self.mama_messages) > 0,
            "has_doctor_context": len(self.doctor_messages) > 0,
            "doctor_session_active": self.doctor_session_active,
            "translator_active": self.translator_active,
            "messages": [
                {
                    "role": m["role"],
                    "content": m["content"],
                    "timestamp": m.get("timestamp", "")
                }
                for m in self.messages
            ]
        }

    def clear_history(self):
        """Очистити всю історію"""
        self.messages = []
        self.mama_messages = []
        self.doctor_messages = []
        self.mama_summary_for_doctor = ""
        self.doctor_summary_for_mama = ""
        self.doctor_session_active = False
        self.translator_messages = []
        self.translator_active = False
        self.mode = "normal"
        self.save_history()
        logger.info("🗑️ Історію очищено")


# Глобальний екземпляр
assistant = AuraAssistant()