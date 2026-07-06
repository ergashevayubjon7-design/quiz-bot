/* ── Telegram WebApp ───────────────────────────────────────── */
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand();
    tg.ready();
}

/* ── Questions ─────────────────────────────────────────────── */
const QUESTIONS = [
    {
        question: "Какая планета Солнечной системы самая большая?",
        options: ["Сатурн", "Нептун", "Юпитер", "Уран"],
        correct: 2,
    },
    {
        question: "В каком году произошло крещение Руси?",
        options: ["862", "988", "1054", "1240"],
        correct: 1,
    },
    {
        question: "Какая страна имеет самую длинную береговую линию в мире?",
        options: ["Россия", "Канада", "Австралия", "Индонезия"],
        correct: 1,
    },
    {
        question: "Кто считается основателем компании Microsoft?",
        options: ["Стив Джобс", "Билл Гейтс", "Марк Цукерберг", "Пол Аллен"],
        correct: 1,
    },
    {
        question: "Какой химический элемент обозначается символом 'Fe'?",
        options: ["Фтор", "Франций", "Фермий", "Железо"],
        correct: 3,
    },
    {
        question: "Какая пустыня является самой большой в мире?",
        options: ["Сахара", "Гоби", "Антарктическая пустыня", "Аравийская"],
        correct: 2,
    },
    {
        question: "В каком году был запущен первый искусственный спутник Земли?",
        options: ["1955", "1957", "1961", "1949"],
        correct: 1,
    },
    {
        question: "Какой язык программирования считается самым старым из активно используемых?",
        options: ["Python", "C", "FORTRAN", "Java"],
        correct: 2,
    },
    {
        question: "Какое животное является символом Всемирного фонда дикой природы (WWF)?",
        options: ["Белый медведь", "Панда", "Тигр", "Кит"],
        correct: 1,
    },
    {
        question: "Как глубоко находится самая глубокая точка океана (Марианская впадина)?",
        options: ["~5 500 м", "~7 800 м", "~11 000 м", "~14 000 м"],
        correct: 2,
    },
    {
        question: "Кто написал роман 'Война и мир'?",
        options: ["Ф.М. Достоевский", "Л.Н. Толстой", "А.С.Пушкин", "И.С. Тургенев"],
        correct: 1,
    },
    {
        question: "Сколько бит в одном байте?",
        options: ["4", "8", "16", "32"],
        correct: 1,
    },
];

const LETTERS = ['A', 'B', 'C', 'D'];

/* ── State ─────────────────────────────────────────────────── */
let state = {
    currentIndex: 0,
    score: 0,
    total: QUESTIONS.length,
    answered: false,
};

/* ── DOM refs ──────────────────────────────────────────────── */
const screens = {
    start: document.getElementById('screen-start'),
    quiz: document.getElementById('screen-quiz'),
    result: document.getElementById('screen-result'),
};

const $ = (id) => document.getElementById(id);

/* ── Screen switching ──────────────────────────────────────── */
function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove('active'));
    screens[name].classList.add('active');
    window.scrollTo(0, 0);
}

/* ── Progress ──────────────────────────────────────────────── */
function updateProgress() {
    const done = state.currentIndex;
    const total = state.total;
    const pct = Math.round((done / total) * 100);

    $('question-counter').textContent = `${done + 1} / ${total}`;
    $('progress-bar').style.width = `${pct}%`;
}

/* ── Render question ───────────────────────────────────────── */
function renderQuestion() {
    const q = QUESTIONS[state.currentIndex];
    if (!q) return;

    state.answered = false;
    updateProgress();

    $('question-text').textContent = q.question;

    const container = $('answers');
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
    const qc = $('question-container');
    qc.style.animation = 'none';
    qc.offsetHeight; // reflow
    qc.style.animation = '';
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

    const q = QUESTIONS[state.currentIndex];
    const buttons = $('answers').querySelectorAll('.answer-btn');
    let isCorrect = selected === q.correct;

    if (isCorrect) {
        state.score += 1;
    }

    buttons.forEach((btn, idx) => {
        btn.classList.add('disabled');
        if (idx === q.correct) {
            btn.classList.add('correct');
        } else if (idx === selected) {
            btn.classList.add('wrong');
        }
    });

    const delay = state.currentIndex < state.total - 1 ? 1000 : 1400;

    setTimeout(() => {
        state.currentIndex += 1;

        if (state.currentIndex >= state.total) {
            showResult();
        } else {
            renderQuestion();
        }
    }, delay);
}

/* ── Result ────────────────────────────────────────────────── */
function showResult() {
    const score = state.score;
    const total = state.total;
    const percent = Math.round((score / total) * 100);

    let emoji, title, message;

    if (percent === 100) {
        emoji = '🏆';
        title = 'Идеально!';
        message = 'Ты ответил на все вопросы правильно! Ты настоящий эрудит! 🌟';
    } else if (percent >= 80) {
        emoji = '🎉';
        title = 'Отлично!';
        message = 'Ты очень много знаешь! Отличный результат!';
    } else if (percent >= 60) {
        emoji = '😊';
        title = 'Хорошо!';
        message = 'Неплохой результат! Попробуй ещё раз улучшить его.';
    } else if (percent >= 40) {
        emoji = '📚';
        title = 'Неплохо';
        message = 'Есть куда расти. Попробуй снова, чтобы подтянуть знания!';
    } else {
        emoji = '🤔';
        title = 'Попробуй ещё';
        message = 'Стоит освежить знания. Не сдавайся!';
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

    // Send result to bot
    sendResultToBot(score, total, percent);

    showScreen('result');
}

/* ── Send data to bot ──────────────────────────────────────── */
function sendResultToBot(score, total, percent) {
    const data = JSON.stringify({ score, total, percent });
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
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(text).catch(() => {});
        $('result-message').textContent = '🔗 Результат скопирован! Отправь друзьям.';
    }
}

/* ── Event listeners ───────────────────────────────────────── */
$('btn-start').addEventListener('click', () => {
    state = { currentIndex: 0, score: 0, total: QUESTIONS.length, answered: false };
    showScreen('quiz');
    renderQuestion();
});

$('btn-retry').addEventListener('click', () => {
    state = { currentIndex: 0, score: 0, total: QUESTIONS.length, answered: false };
    showScreen('quiz');
    renderQuestion();
});

$('btn-share').addEventListener('click', shareResult);

/* ── Init ──────────────────────────────────────────────────── */
if (tg) {
    tg.onEvent('themeChanged', () => {
        // Telegram handles CSS variable updates automatically
    });
}

showScreen('start');
