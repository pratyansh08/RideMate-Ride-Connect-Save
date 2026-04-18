import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client.js";
import { setToken } from "../utils/auth.js";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

const Login = () => {
  const navigate = useNavigate();
  const googleButtonRef = useRef(null);
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleReadyError, setGoogleReadyError] = useState("");

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !googleButtonRef.current) {
      return undefined;
    }

    let cancelled = false;
    const existingScript = document.querySelector('script[data-google-identity="true"]');

    const initializeGoogle = () => {
      if (cancelled || !window.google?.accounts?.id || !googleButtonRef.current) {
        return;
      }

      googleButtonRef.current.innerHTML = "";
      setGoogleReadyError("");
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        shape: "pill",
        text: "continue_with",
        width: googleButtonRef.current.offsetWidth || 360,
      });
    };

    const waitForGoogleAndInitialize = () => {
      let attempts = 0;
      const maxAttempts = 20;
      const intervalId = window.setInterval(() => {
        attempts += 1;
        if (cancelled) {
          window.clearInterval(intervalId);
          return;
        }
        if (window.google?.accounts?.id) {
          window.clearInterval(intervalId);
          initializeGoogle();
          return;
        }
        if (attempts >= maxAttempts) {
          window.clearInterval(intervalId);
          setGoogleReadyError("Google sign-in failed to load. Please refresh.");
        }
      }, 200);
    };

    if (existingScript) {
      if (window.google?.accounts?.id) {
        initializeGoogle();
      } else {
        waitForGoogleAndInitialize();
      }
      return () => {
        cancelled = true;
      };
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.dataset.googleIdentity = "true";
    script.onload = initializeGoogle;
    script.onerror = () => {
      setGoogleReadyError("Unable to load Google sign-in script.");
    };
    document.head.appendChild(script);

    return () => {
      cancelled = true;
    };
  }, []);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const completeLogin = (payload) => {
    setToken(payload.access);
    localStorage.setItem("refreshToken", payload.refresh);
    navigate("/profile");
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
      completeLogin(response.data);
    } catch (err) {
      setError("Login failed. Check username/password.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCredential = async (googleResponse) => {
    const token = googleResponse?.credential;
    if (!token) {
      setError("Google sign-in failed. Please try again.");
      return;
    }

    setError("");
    setGoogleLoading(true);
    try {
      const response = await api.post("/api/accounts/google-login/", { token });
      completeLogin(response.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Google sign-in failed. Please try again.");
    } finally {
      setGoogleLoading(false);
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
          {GOOGLE_CLIENT_ID ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-xs uppercase tracking-[0.3em] text-slate/40">
                <span className="h-px flex-1 bg-mist" />
                <span>or</span>
                <span className="h-px flex-1 bg-mist" />
              </div>
              <div ref={googleButtonRef} className="min-h-11 w-full" />
              {googleReadyError && (
                <p className="text-xs text-red-600">{googleReadyError}</p>
              )}
              {googleLoading && (
                <p className="text-xs text-slate/60">Signing in with Google...</p>
              )}
            </div>
          ) : (
            <p className="text-xs text-slate/50">
              Google sign-in will appear after `VITE_GOOGLE_CLIENT_ID` is configured.
            </p>
          )}
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
