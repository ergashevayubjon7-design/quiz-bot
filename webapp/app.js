/* ── Telegram WebApp ───────────────────────────────────────── */
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand();
    tg.ready();
}

/* ── Mode detection ────────────────────────────────────────── */
const urlParams = new URLSearchParams(window.location.search);
const GAME_MODE = urlParams.get('mode') || 'regular'; // 'regular' | 'prize'

/* ── Regular Questions ────────────────────────────────────── */
const REGULAR_QUESTIONS = [
    { question: "Какая планета Солнечной системы самая большая?", options: ["Сатурн", "Нептун", "Юпитер", "Уран"], correct: 2 },
    { question: "В каком году произошло крещение Руси?", options: ["862", "988", "1054", "1240"], correct: 1 },
    { question: "Какая страна имеет самую длинную береговую линию в мире?", options: ["Россия", "Канада", "Австралия", "Индонезия"], correct: 1 },
    { question: "Кто считается основателем компании Microsoft?", options: ["Стив Джобс", "Билл Гейтс", "Марк Цукерберг", "Пол Аллен"], correct: 1 },
    { question: "Какой химический элемент обозначается символом 'Fe'?", options: ["Фтор", "Франций", "Фермий", "Железо"], correct: 3 },
    { question: "Какая пустыня является самой большой в мире?", options: ["Сахара", "Гоби", "Антарктическая пустыня", "Аравийская"], correct: 2 },
    { question: "В каком году был запущен первый искусственный спутник Земли?", options: ["1955", "1957", "1961", "1949"], correct: 1 },
    { question: "Какой язык программирования считается самым старым из активно используемых?", options: ["Python", "C", "FORTRAN", "Java"], correct: 2 },
    { question: "Какое животное является символом Всемирного фонда дикой природы (WWF)?", options: ["Белый медведь", "Панда", "Тигр", "Кит"], correct: 1 },
    { question: "Кто написал роман 'Война и мир'?", options: ["Ф.М. Достоевский", "Л.Н. Толстой", "А.С. Пушкин", "И.С. Тургенев"], correct: 1 },
    { question: "Сколько бит в одном байте?", options: ["4", "8", "16", "32"], correct: 1 },
    { question: "Как глубоко находится самая глубокая точка океана (Марианская впадина)?", options: ["~5 500 м", "~7 800 м", "~11 000 м", "~14 000 м"], correct: 2 },
];

/* ── Prize Questions (Anti-AI / Human Experience) ──────────── */
/* Questions designed to be easy for humans but hard for AI/agents:
   - human sensory experience
   - cultural-specific knowledge
   - embodied cognition / common sense
   - visual / spatial intuition
   - trick questions that AI tends to overthink */
const PRIZE_QUESTIONS = [
    {
        question: "🧩 Какое слово зашифровано? 🐝 + 🌊",
        options: ["Пчеловод", "Морепродукт", "Медведь", "Пляж"],
        correct: 0,
        hint: "Пчела + вода → ???"
    },
    {
        question: "👃 Что чувствует человек, когда говорит: «У меня кровь стынет в жилах»?",
        options: ["Холод", "Страх / шок", "Боль", "Головокружение"],
        correct: 1,
        hint: "Это метафора, а не про температуру"
    },
    {
        question: "🕵️ Если Петина мама — это Мария, а папа — Иван, то кем Петя приходится Марии?",
        options: ["Племянником", "Сыном", "Братом", "Внуком"],
        correct: 1,
        hint: "Семейные связи"
    },
    {
        question: "🎨 Если долго смотреть на красный круг, а потом перевести взгляд на белую стену — что увидит человек?",
        options: ["Красный круг", "Зелёный круг", "Ничего", "Серый круг"],
        correct: 1,
        hint: "Оптическая иллюзия — противоположный цвет"
    },
    {
        question: "🧮 Сколько всего треугольников в звезде Давида (шестиконечной)?",
        options: ["6", "8", "12", "18"],
        correct: 1,
        hint: "Посчитай маленькие треугольники, а потом большие"
    },
    {
        question: "🤷 Какое из этих ощущений человек НЕ способен описать словами?",
        options: ["Вкус лимона", "Цвет ультрафиолета", "Запах скошенной травы", "Звук грома"],
        correct: 1,
        hint: "Человек не может увидеть этот цвет"
    },
    {
        question: "🧊 Что произойдёт с водой в стакане, если её заморозить?",
        options: ["Объём уменьшится", "Объём увеличится", "Объём не изменится", "Вода испарится"],
        correct: 1,
        hint: "Вспомни, что лёгче — лёд или вода?"
    },
    {
        question: "🎲 Какой месяц пропущен в ряду: Январь — Март — Май — ? — Сентябрь",
        options: ["Июнь", "Июль", "Август", "Октябрь"],
        correct: 1,
        hint: "Месяцы через один"
    },
    {
        question: "🤔 Что тяжелее: 1 кг ваты или 1 кг железа?",
        options: ["Вата", "Железо", "Одинаково", "Зависит от гравитации"],
        correct: 2,
        hint: "Вес один и тот же..."
    },
    {
        question: "🧠 Когда человек говорит 'чешет затылок', что он обычно выражает?",
        options: ["Радость", "Задумчивость / недоумение", "Злость", "Страх"],
        correct: 1,
        hint: "Жест-паразит, который выдает размышления"
    }
];

const LETTERS = ['A', 'B', 'C', 'D'];

/* ── State ─────────────────────────────────────────────────── */
let state = {
    currentIndex: 0,
    score: 0,
    total: 0,
    answered: false,
    mode: GAME_MODE,
};

/* ── DOM refs ──────────────────────────────────────────────── */
const screens = {
    start: document.getElementById('screen-start'),
    quiz: document.getElementById('screen-quiz'),
    prizeQuiz: document.getElementById('screen-prize-quiz'),
    result: document.getElementById('screen-result'),
    prizeResult: document.getElementById('screen-prize-result'),
};

const levelOverlay = document.getElementById('level-complete');

const $ = (id) => document.getElementById(id);

/* ── Screen switching ──────────────────────────────────────── */
function showScreen(name) {
    Object.values(screens).forEach((s) => {
        if (s) s.classList.remove('active');
    });
    if (screens[name]) screens[name].classList.add('active');
    window.scrollTo(0, 0);
}

/* ── Progress ──────────────────────────────────────────────── */
function updateProgress() {
    const done = state.currentIndex;
    const total = state.total;
    const pct = Math.round((done / total) * 100);

    const prefix = state.mode === 'prize' ? 'prize-' : '';
    $(`${prefix}question-counter`) && ($(`${prefix}question-counter`).textContent = `${done + 1} / ${total}`);
    $(`${prefix}progress-bar`) && ($(`${prefix}progress-bar`).style.width = `${pct}%`);

    // Score display for regular mode
    if (state.mode === 'regular') {
        $('score-display').textContent = `⭐ ${state.score}`;
    }

    // Level label for prize mode
    if (state.mode === 'prize') {
        const levelNames = ['', 'Начинающий', 'Любопытный', 'Мыслитель', 'Эрудит', 'Интеллектуал', 'Профессор', 'Гений', 'Легенда', 'Бог знаний', 'Абсолют'];
        const level = Math.min(state.currentIndex + 1, 10);
        $('prize-level-label').textContent = `УРОВЕНЬ ${level} — ${levelNames[level] || ''}`;
    }
}

/* ── Render question (regular) ─────────────────────────────── */
function renderQuestion() {
    const questions = state.mode === 'prize' ? PRIZE_QUESTIONS : REGULAR_QUESTIONS;
    const q = questions[state.currentIndex];
    if (!q) return;

    state.answered = false;
    updateProgress();

    const prefix = state.mode === 'prize' ? 'prize-' : '';
    $(`${prefix}question-text`).textContent = q.question;

    const container = $(`${prefix}answers`);
    container.innerHTML = '';

    q.options.forEach((text, idx) => {
        const btn = document.createElement('button');
        btn.className = 'answer-btn';
        btn.dataset.index = idx;
        btn.innerHTML = `<span class="answer-letter">${LETTERS[idx]}</span>${escapeHtml(text)}`;
        btn.addEventListener('click', () => handleAnswer(idx));
        container.appendChild(btn);
    });

    // Re-trigger animation
    const qc = $(`${prefix}question-container`);
    if (qc) {
        qc.style.animation = 'none';
        qc.offsetHeight; // reflow
        qc.style.animation = '';
    }
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

/* ── Handle answer ─────────────────────────────────────────── */
function handleAnswer(selected) {
    if (state.answered) return;
    state.answered = true;

    const questions = state.mode === 'prize' ? PRIZE_QUESTIONS : REGULAR_QUESTIONS;
    const q = questions[state.currentIndex];

    const prefix = state.mode === 'prize' ? 'prize-' : '';
    const buttons = $(`${prefix}answers`).querySelectorAll('.answer-btn');

    let isCorrect = selected === q.correct;
    if (isCorrect) state.score += 1;

    buttons.forEach((btn, idx) => {
        btn.classList.add('disabled');
        if (idx === q.correct) {
            btn.classList.add('correct');
        } else if (idx === selected) {
            btn.classList.add('wrong');
        }
    });

    // Show level overlay for prize mode
    if (state.mode === 'prize') {
        showLevelOverlay(isCorrect);
    }

    const delay = state.mode === 'prize' ? 1200 : (state.currentIndex < state.total - 1 ? 1000 : 1400);

    setTimeout(() => {
        if (state.mode === 'prize') hideLevelOverlay();
        state.currentIndex += 1;

        if (state.currentIndex >= state.total) {
            showFinalResult();
        } else {
            renderQuestion();
        }
    }, delay);
}

/* ── Level overlay (prize mode) ────────────────────────────── */
function showLevelOverlay(correct) {
    if (!levelOverlay) return;
    const emoji = correct ? '✅' : '❌';
    const text = correct ? 'Верно!' : 'Неверно!';
    const sub = correct ? `+1 балл (${state.score}/${state.total})` : `Правильный ответ был под буквой ${LETTERS[getCorrectAnswer()]}`;

    document.getElementById('level-emoji').textContent = emoji;
    document.getElementById('level-text').textContent = text;
    document.getElementById('level-sub').textContent = sub;

    levelOverlay.style.display = 'flex';
    levelOverlay.className = 'level-overlay';
    levelOverlay.classList.add(correct ? 'level-correct' : 'level-wrong');
}

function hideLevelOverlay() {
    if (levelOverlay) levelOverlay.style.display = 'none';
}

function getCorrectAnswer() {
    const questions = PRIZE_QUESTIONS;
    const q = questions[state.currentIndex];
    return q ? q.correct : -1;
}

/* ── Final Result ──────────────────────────────────────────── */
function showFinalResult() {
    const score = state.score;
    const total = state.total;
    const percent = Math.round((score / total) * 100);

    if (state.mode === 'prize') {
        showPrizeResult(score, total, percent);
    } else {
        showRegularResult(score, total, percent);
    }
}

function showRegularResult(score, total, percent) {
    let emoji, title, message;

    if (percent === 100) {
        emoji = '🏆'; title = 'Идеально!'; message = 'Ты ответил на все вопросы правильно! Ты настоящий эрудит! 🌟';
    } else if (percent >= 80) {
        emoji = '🎉'; title = 'Отлично!'; message = 'Ты очень много знаешь! Отличный результат!';
    } else if (percent >= 60) {
        emoji = '😊'; title = 'Хорошо!'; message = 'Неплохой результат! Попробуй ещё раз улучшить его.';
    } else if (percent >= 40) {
        emoji = '📚'; title = 'Неплохо'; message = 'Есть куда расти. Попробуй снова, чтобы подтянуть знания!';
    } else {
        emoji = '🤔'; title = 'Попробуй ещё'; message = 'Стоит освежить знания. Не сдавайся!';
    }

    $('result-emoji').textContent = emoji;
    $('result-title').textContent = title;
    $('result-score-num').textContent = score;
    $('result-total-num').textContent = total;
    $('result-percent-text').textContent = `${percent}%`;
    $('result-message').textContent = message;

    // Animate the ring
    const ring = $('result-ring');
    const circumference = 339.292;
    const offset = circumference - (percent / 100) * circumference;
    setTimeout(() => {
        ring.style.transition = 'stroke-dashoffset 1s ease-out';
        ring.style.strokeDashoffset = offset;
    }, 300);

    sendResultToBot(score, total, percent, 'regular');
    showScreen('result');
}

function showPrizeResult(score, total, percent) {
    $('prize-final-score').textContent = score;
    $('prize-final-total').textContent = total;

    const fillPct = Math.round((score / total) * 100);
    $('prize-final-fill').style.width = `${fillPct}%`;

    let label;
    if (score === 10) label = '🎉 Абсолютный чемпион! Ты непобедим!';
    else if (score >= 8) label = '🏆 Фантастика! Ты претендент на приз!';
    else if (score >= 6) label = '👏 Отлично! У тебя есть шанс на топ-3!';
    else if (score >= 4) label = '💪 Хороший результат! Попробуй ещё раз.';
    else label = '📚 Попробуй ещё! В следующий раз получится лучше.';

    $('prize-final-label').textContent = label;

    sendResultToBot(score, total, percent, 'prize');
    showScreen('prizeResult');
}

/* ── Send data to bot ──────────────────────────────────────── */
function sendResultToBot(score, total, percent, mode) {
    const data = JSON.stringify({ score, total, percent, mode });
    if (tg) {
        tg.sendData(data);
    } else {
        console.log('[Quiz] Result (no Telegram context):', data);
    }
}

/* ── Share ─────────────────────────────────────────────────── */
function shareResult() {
    const score = state.score;
    const total = state.total;
    const percent = Math.round((score / total) * 100);

    const text = `🧠 Я набрал ${score}/${total} (${percent}%) в Quiz Bot! Попробуй и ты! 🎮`;

    if (tg) {
        tg.switchInlineQuery(text, ['users', 'groups']);
    } else {
        navigator.clipboard.writeText(text).catch(() => {});
        $('result-message').textContent = '🔗 Результат скопирован! Отправь друзьям.';
    }
}

/* ── Initialize game mode ──────────────────────────────────── */
function initGame() {
    if (GAME_MODE === 'prize') {
        // Prize mode — skip start screen
        $('start-subtitle').textContent = '🏆 Призовая игра — 10 уровней!';
        state = { currentIndex: 0, score: 0, total: PRIZE_QUESTIONS.length, answered: false, mode: 'prize' };
        showScreen('prizeQuiz');
        renderQuestion();
    } else {
        // Regular mode — show start screen
        state = { currentIndex: 0, score: 0, total: REGULAR_QUESTIONS.length, answered: false, mode: 'regular' };
        showScreen('start');
    }
}

/* ── Event listeners ───────────────────────────────────────── */
$('btn-start').addEventListener('click', () => {
    state = { currentIndex: 0, score: 0, total: REGULAR_QUESTIONS.length, answered: false, mode: 'regular' };
    showScreen('quiz');
    renderQuestion();
});

$('btn-retry').addEventListener('click', () => {
    state = { currentIndex: 0, score: 0, total: REGULAR_QUESTIONS.length, answered: false, mode: 'regular' };
    showScreen('quiz');
    renderQuestion();
});

$('btn-share').addEventListener('click', shareResult);

$('btn-prize-close')?.addEventListener('click', () => {
    // Close the mini app
    if (tg) tg.close();
});

/* ── Init ──────────────────────────────────────────────────── */
if (tg) {
    tg.onEvent('themeChanged', () => {
        // Telegram handles CSS variable updates automatically
    });
}

initGame();
