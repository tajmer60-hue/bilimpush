// DOM-тест демо через РЕАЛЬНЫЕ КЛИКИ (как в просмотрщике) + симуляция песочницы:
// localStorage бросает исключение, location.hash не используется приложением вовсе.
// Запуск: NODE_PATH=/tmp/jsdomtest/node_modules node demo/tests/dom_test.js
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf-8");

const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => {
  if (!String(e.message).includes("scrollTo")) errors.push("jsdomError: " + e.message);
});
vc.on("error", (...a) => errors.push("console.error: " + a.join(" ")));

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  url: "https://bilim.local/demo/",
  virtualConsole: vc,
  beforeParse(window) {
    // симуляция sandboxed iframe: localStorage недоступен
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() { throw new Error("SecurityError: localStorage blocked"); },
    });
    window.confirm = () => true;
  },
});
const { window } = dom;
const doc = window.document;

let failures = 0;
function step(name, fn) {
  try { fn(); console.log("PASS " + name); }
  catch (e) { failures++; console.log("FAIL " + name + " — " + e.message); }
}
const assert = (cond, msg) => { if (!cond) throw new Error(msg || "assert"); };
const click = el => { assert(el, "element not found"); el.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
const appHtml = () => doc.getElementById("app").innerHTML;

setTimeout(() => {
  console.log("JS errors on load:", errors.length ? errors : "none");

  step("auth screen rendered (без формы, кнопка data-action)", () => {
    assert(appHtml().includes("Bilim"), "no app content");
    assert(doc.getElementById("fName"), "no name input");
    assert(doc.querySelector('[data-action="login"]'), "no login button");
    assert(!doc.querySelector("form"), "form should not exist");
    assert(!appHtml().includes("onclick="), "inline onclick found!");
  });

  step("короткое имя отклоняется", () => {
    doc.getElementById("fName").value = "A";
    click(doc.querySelector('[data-action="login"]'));
    assert(doc.getElementById("nameErr").style.display === "block", "no error shown");
  });

  step("вход кликом по кнопке", () => {
    doc.getElementById("fName").value = "Аружан";
    click(doc.querySelector('[data-action="login"]'));
    assert(appHtml().includes("Сәлем"), "dashboard not shown; head: " + appHtml().slice(0, 200));
  });

  step("клик по «Предметы» в шапке", () => {
    click(doc.querySelector('[data-go="#/subjects"]'));
    assert(appHtml().includes("Математика"), "no subjects grid");
  });

  step("клик по карточке предмета", () => {
    click(doc.querySelector(".subject-card"));
    assert(appHtml().includes("topic-item"), "no topics list");
  });

  step("клик по теме → теория", () => {
    click(doc.querySelector(".topic-item"));
    assert(appHtml().includes("theory-content"), "no theory");
    assert(doc.querySelector('[data-action="start-test"]'), "no start-test button");
  });

  step("клик «Пройти тест» → 10 вопросов", () => {
    click(doc.querySelector('[data-action="start-test"]'));
    assert(appHtml().includes("Вопрос 1 из"), "test not started");
    assert(doc.querySelectorAll(".q-card").length === 10, "wrong question count");
  });

  step("клик по варианту ответа помечает его", () => {
    const opt = doc.querySelector(".q-card .option");
    click(opt);
    assert(doc.querySelector(".q-card .option").classList.contains("selected"), "option not selected");
  });

  step("submit с неполными ответами → тост, без падения", () => {
    click(doc.querySelector('[data-action="submit"]'));
    assert(doc.querySelector(".toast"), "no toast for unanswered");
    assert(appHtml().includes("Вопрос 1 из"), "test screen lost");
  });

  step("ответить на все НЕверно (реальными кликами) и отправить", () => {
    const qs = window.eval("TEST_STATE.attempt.questions.map(q => ({id: q.id, correct: q.correct, n: q.options.length}))");
    for (const q of qs) {
      const opts = doc.querySelectorAll(`#qcard-${q.id} .option`);
      click(opts[(q.correct + 1) % q.n]);
    }
    click(doc.querySelector('[data-action="submit"]'));
    assert(appHtml().includes("Тест не сдан"), "expected fail screen");
    assert(appHtml().includes("Разбор ответов"), "no review");
    assert(appHtml().includes("Пояснение"), "no explanations");
  });

  step("клик «Пройти новый тест» → адаптивный ретест с баннером", () => {
    click(doc.querySelector('[data-action="start-test"]'));
    assert(appHtml().includes("Повторная попытка"), "no retry banner");
    const info = window.eval("({retry: TEST_STATE.attempt.is_retry, n: TEST_STATE.attempt.questions.length})");
    assert(info.retry === true && info.n === 10, "retry state wrong");
  });

  step("ответить ВЕРНО (кликами) → тест сдан, тема passed", () => {
    const qs = window.eval("TEST_STATE.attempt.questions.map(q => ({id: q.id, correct: q.correct}))");
    for (const q of qs) {
      click(doc.querySelectorAll(`#qcard-${q.id} .option`)[q.correct]);
    }
    click(doc.querySelector('[data-action="submit"]'));
    assert(appHtml().includes("Тест сдан"), "expected pass screen");
    const prog = window.eval("topicProgress(TEST_STATE.attempt.topic_id)");
    assert(prog.status === "passed" && prog.best_score === 1, "progress wrong: " + JSON.stringify(prog));
  });

  step("клик «На главную» → дашборд с прогрессом", () => {
    click(doc.querySelector('[data-go="#/home"]'));
    assert(appHtml().includes("тем сдано"), "no stats");
    const passed = window.eval("document.querySelector('.stat-num').textContent");
    assert(passed.startsWith("1"), "passed count not 1: " + passed);
  });

  step("клик по слабой теме / истории не падает", () => {
    click(doc.querySelector('[data-go="#/subjects"]'));
    assert(appHtml().includes("subjects-grid"), "subjects broken");
  });

  console.log("\nTotal JS errors:", errors.length ? errors : "none");
  console.log(failures === 0 && errors.length === 0 ? "DOM TESTS OK ✅" : "DOM TESTS FAILED ❌");
  process.exit(failures === 0 && errors.length === 0 ? 0 : 1);
}, 300);
