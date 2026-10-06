"""End-to-end тест Bilim+: frontend, auth, тесты, адаптивность, прогресс."""
import json
import os
import sqlite3
import urllib.request

BASE = "http://localhost:8000"
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "backend", "bilim.db")


def req(method, path, data=None, token=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def jreq(method, path, data=None, token=None):
    st, body = req(method, path, data, token)
    try:
        return st, json.loads(body)
    except Exception:
        return st, body


def main():
    ok = True

    def check(label, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(("PASS " if cond else "FAIL ") + label + (" " + str(extra) if extra else ""))

    # frontend
    st, body = req("GET", "/")
    check("frontend index served", st == 200 and b"Bilim" in body)
    st, body = req("GET", "/css/style.css")
    check("css served", st == 200 and len(body) > 1000)
    st, body = req("GET", "/js/app.js")
    check("app.js served", st == 200 and len(body) > 1000)

    # register fresh user (уникальный e-mail на каждый запуск)
    import time
    email = f"student{int(time.time())}@mail.kz"
    st, d = jreq("POST", "/api/auth/register",
                 {"name": "Тест Ученик", "email": email, "password": "test123"})
    check("register", st == 200, st)
    token = d["token"]

    st, subjects = jreq("GET", "/api/subjects", token=token)
    check("subjects: 9", st == 200 and len(subjects) == 9, len(subjects) if st == 200 else st)
    tid = subjects[0]["sections"][0]["topics"][3]["id"]

    db = sqlite3.connect(DB_PATH)
    correct = {qid: corr for qid, corr in db.execute(
        "SELECT id, correct FROM questions WHERE topic_id=?", (tid,))}

    # fail attempt
    st, a1 = jreq("POST", f"/api/topics/{tid}/test", token=token)
    check("start test", st == 200 and len(a1["questions"]) == 10 and a1.get("topic_title"),
          a1.get("topic_title"))
    wrong = [{"question_id": q["id"], "selected": (correct[q["id"]] + 1) % len(q["options"])}
             for q in a1["questions"]]
    st, r1 = jreq("POST", f"/api/attempts/{a1['attempt_id']}/submit", {"answers": wrong}, token=token)
    check("submit fail: score 0, not passed", st == 200 and r1["score"] == 0.0 and not r1["passed"],
          (r1.get("score"), r1.get("passed")))
    check("retry hint present", bool(r1.get("retry_hint")))

    # adaptive retry
    st, a2 = jreq("POST", f"/api/topics/{tid}/test", token=token)
    check("retry: is_retry True", st == 200 and a2["is_retry"], a2.get("is_retry"))
    new_ids = {q["id"] for q in a2["questions"]}
    wrong_ids = {r["question_id"] for r in r1["results"] if not r["is_correct"]}
    check("retry includes wrong questions", len(wrong_ids & new_ids) >= 6,
          f"{len(wrong_ids & new_ids)} of {len(wrong_ids)}")
    check("retry_reason present", bool(a2.get("retry_reason")))

    # pass attempt
    good = [{"question_id": q["id"], "selected": correct[q["id"]]} for q in a2["questions"]]
    st, r2 = jreq("POST", f"/api/attempts/{a2['attempt_id']}/submit", {"answers": good}, token=token)
    check("submit pass: 100%, passed", st == 200 and r2["score"] == 1.0 and r2["passed"],
          (r2.get("score"), r2.get("passed")))

    st, t = jreq("GET", f"/api/topics/{tid}", token=token)
    check("topic status passed, best 1.0, attempts 2",
          t["status"] == "passed" and t["best_score"] == 1.0 and t["attempts_count"] == 2,
          (t["status"], t["best_score"], t["attempts_count"]))

    st, dash = jreq("GET", "/api/progress", token=token)
    check("dashboard: passed=1, tests=2", dash["topics_passed"] == 1 and dash["tests_taken"] == 2,
          (dash.get("topics_passed"), dash.get("tests_taken")))
    check("dashboard: weak topics empty after pass", len(dash["weak_topics"]) == 0,
          len(dash["weak_topics"]))

    # double submit blocked
    st, r3 = jreq("POST", f"/api/attempts/{a2['attempt_id']}/submit", {"answers": good}, token=token)
    check("double submit blocked (400)", st == 400, st)

    # unauthorised access
    st, _ = jreq("GET", "/api/progress")
    check("progress requires auth (401/403)", st in (401, 403), st)

    print("\n" + ("ALL CHECKS PASSED ✅" if ok else "SOME CHECKS FAILED ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
