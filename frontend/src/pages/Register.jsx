import { useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client.js";

const Register = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    gender: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setTouched(true);
    if (!form.username || !form.email || !form.password) {
      setError("Username, email, and password are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.post("/api/accounts/register/", form);
      navigate("/login");
    } catch (err) {
      const data = err?.response?.data;
      if (data && typeof data === "object") {
        const messages = Object.entries(data)
          .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : value}`)
          .join(" | ");
        setError(messages || "Registration failed.");
      } else {
        setError("Registration failed. Please check your inputs.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl rounded-3xl bg-white/90 p-8 shadow-glow">
      <h1 className="font-display text-3xl font-bold text-slate">Create account</h1>
      <p className="mt-2 text-sm text-slate/70">
        Join RideMate and start offering or booking rides.
      </p>
      <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Username</label>
          <input
            name="username"
            value={form.username}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Email</label>
          <input
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Gender</label>
          <select
            name="gender"
            value={form.gender}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
          >
            <option value="">Select</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="text-xs font-semibold uppercase text-slate/70">Password</label>
          <input
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        {error && <p className="text-sm text-red-600 md:col-span-2">{error}</p>}
        {touched && (!form.username || !form.email || !form.password) && (
          <p className="text-xs text-slate/60 md:col-span-2">
            Fill in username, email, and password.
          </p>
        )}
        <button type="submit" disabled={loading} className="btn-primary md:col-span-2">
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>
    </div>
  );
};

export default Register;
