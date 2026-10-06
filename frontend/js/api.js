/* API-клиент Bilim+ */
const API = {
  token: localStorage.getItem("bilim_token") || null,
  user: JSON.parse(localStorage.getItem("bilim_user") || "null"),

  saveSession(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem("bilim_token", token);
    localStorage.setItem("bilim_user", JSON.stringify(user));
  },
  clearSession() {
    this.token = null;
    this.user = null;
    localStorage.removeItem("bilim_token");
    localStorage.removeItem("bilim_user");
  },

  async request(method, path, data) {
    const headers = { "Content-Type": "application/json" };
    if (this.token) headers["Authorization"] = "Bearer " + this.token;
    const resp = await fetch("/api" + path, {
      method,
      headers,
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const err = new Error(json.detail
        ? (typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail))
        : "Ошибка сервера (" + resp.status + ")");
      err.status = resp.status;
      throw err;
    }
    return json;
  },

  register(name, email, password) {
    return this.request("POST", "/auth/register", { name, email, password });
  },
  login(email, password) {
    return this.request("POST", "/auth/login", { email, password });
  },
  subjects() { return this.request("GET", "/subjects"); },
  topic(id) { return this.request("GET", "/topics/" + id); },
  markRead(id) { return this.request("POST", "/topics/" + id + "/read"); },
  startTest(id) { return this.request("POST", "/topics/" + id + "/test"); },
  submit(attemptId, answers) {
    return this.request("POST", "/attempts/" + attemptId + "/submit", { answers });
  },
  progress() { return this.request("GET", "/progress"); },
};
