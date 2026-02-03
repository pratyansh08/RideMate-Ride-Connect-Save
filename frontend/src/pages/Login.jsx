import { useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client.js";
import { setToken } from "../utils/auth.js";

const Login = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setTouched(true);
    if (!form.username || !form.password) {
      setError("Please fill in username and password.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await api.post("/api/login/", form);
      setToken(response.data.access);
      localStorage.setItem("refreshToken", response.data.refresh);
      navigate("/trips/search");
    } catch (err) {
      setError("Login failed. Check username/password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-10">
      <div className="grid gap-10 md:grid-cols-2">
      <div className="relative overflow-hidden rounded-[32px] bg-white p-8 shadow-glow">
        <div className="absolute right-0 top-0 h-24 w-24 -translate-y-8 translate-x-8 rounded-full bg-black/10 blur-2xl" />
        <h1 className="font-display text-3xl font-bold text-slate">Welcome back</h1>
        <p className="mt-2 text-sm text-slate/70">
          Log in to manage your trips, bookings, reviews, and chats in one place.
        </p>
        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="text-xs font-semibold uppercase text-slate/70">Username</label>
            <input
              name="username"
              value={form.username}
              onChange={handleChange}
              className="mt-2 w-full rounded-2xl border border-mist bg-fog px-4 py-3 shadow-sm"
              placeholder="Enter username"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase text-slate/70">Password</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              className="mt-2 w-full rounded-2xl border border-mist bg-fog px-4 py-3 shadow-sm"
              placeholder="Enter password"
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>
        {touched && (!form.username || !form.password) && (
          <p className="mt-3 text-xs text-slate/60">All fields are required.</p>
        )}
      </div>
      <div className="rounded-[32px] border border-mist bg-white p-8">
        <h2 className="font-display text-2xl font-semibold text-slate">
          First time on RideMate?
        </h2>
        <p className="mt-2 text-sm text-slate/70">
          Create an account to post rides, book seats, and build your rating profile.
        </p>
        <div className="mt-6 grid gap-3 text-sm text-slate/70">
          <div className="rounded-2xl bg-fog p-4">
            <p className="font-semibold text-slate">Quick matches</p>
            <p className="mt-1">Search by city, date, price, and seats.</p>
          </div>
          <div className="rounded-2xl bg-fog p-4">
            <p className="font-semibold text-slate">Trusted profiles</p>
            <p className="mt-1">Ratings and reviews for safer rides.</p>
          </div>
        </div>
        <button type="button" onClick={() => navigate("/register")} className="btn-outline mt-6">
          Create an account
        </button>
      </div>
    </div>
      <section className="rounded-[28px] border border-mist bg-white p-8">
        <h2 className="font-display text-2xl font-semibold text-slate">About RideMate</h2>
        <p className="mt-3 text-sm leading-6 text-slate/70">
          RideMate makes travelling smarter and more affordable by connecting people heading in
          the same direction. From ride creation to booking, chatting, and reviewing drivers —
          everything is designed to be simple, fast, and secure.
        </p>
        <div className="mt-6 rounded-2xl bg-fog p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate/60">
            Creator Line
          </p>
          <p className="mt-2 text-sm font-semibold text-slate">
            Created &amp; Developed by Pratyansh Singh
          </p>
          <p className="mt-1 text-sm text-slate/70">
            Turning real-world problems into scalable web applications.
          </p>
        </div>
      </section>
    </div>
  );
};

export default Login;
