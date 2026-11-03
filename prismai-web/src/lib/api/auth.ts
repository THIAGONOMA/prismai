import { apiFetch, setToken, clearToken } from "./client";

export const authApi = {
  login: async (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const res = await apiFetch<{ access_token: string }>("/v1/auth/token", {
      method: "POST",
      body: form,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    setToken(res.access_token);
    return res;
  },
  logout: () => clearToken(),
};
