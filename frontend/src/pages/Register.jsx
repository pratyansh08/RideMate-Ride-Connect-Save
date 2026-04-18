import { useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client.js";

const Register = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    phone: "",
    password: "",
    gender: "",
  });
  const [otpMethod, setOtpMethod] = useState("email");
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpInfo, setOtpInfo] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleRequestOtp = async () => {
    setError("");
    setOtpInfo("");
    const payload = {
      channel: otpMethod,
      email: form.email,
      phone: form.phone,
    };
    if (otpMethod === "email" && !form.email) {
      setError("Email required for email OTP.");
      return;
    }
    if (otpMethod === "phone" && !form.phone) {
      setError("Phone required for mobile OTP.");
      return;
    }

    setOtpLoading(true);
    try {
      const response = await api.post("/api/accounts/request-otp/", payload);
      setOtpSent(true);
      const debugOtp = response.data?.debug_otp ? ` OTP: ${response.data.debug_otp}` : "";
      setOtpInfo(`${response.data?.message || "OTP sent."}${debugOtp}`);
    } catch (err) {
      const data = err?.response?.data;
      const errors = data?.errors ?? data;
      if (errors && typeof errors === "object") {
        const messages = Object.entries(errors)
          .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : value}`)
          .join(" | ");
        setError(messages || "Unable to send OTP.");
      } else {
        setError("Unable to send OTP.");
      }
    } finally {
      setOtpLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setTouched(true);
    if (!form.username || !form.email || !form.password || !otpCode) {
      setError("Username, email, password and OTP are required.");
      return;
    }
    if (otpMethod === "phone" && !form.phone) {
      setError("Phone number is required for mobile OTP.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.post("/api/accounts/register/", {
        ...form,
        otp_channel: otpMethod,
        otp_code: otpCode,
      });
      navigate("/login");
    } catch (err) {
      const data = err?.response?.data;
      const errors = data?.errors ?? data;

      if (errors && typeof errors === "object") {
        const messages = Object.entries(errors)
          .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : value}`)
          .join(" | ");
        setError(messages || "Registration failed.");
      } else if (typeof data === "string" && data.trim()) {
        setError(`Registration failed. Server response: ${data.trim()}`);
      } else if (err?.response?.status) {
        setError(`Registration failed. Server error (${err.response.status}).`);
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
        Join RideMate and verify your email or mobile with OTP.
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
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">OTP Method</label>
          <select
            value={otpMethod}
            onChange={(event) => {
              setOtpMethod(event.target.value);
              setOtpSent(false);
              setOtpCode("");
              setOtpInfo("");
            }}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
          >
            <option value="email">Email OTP</option>
            <option value="phone">Mobile OTP</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Phone</label>
          <input
            name="phone"
            value={form.phone}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            placeholder="Enter phone number"
            disabled={otpMethod !== "phone"}
          />
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
        <div className="md:col-span-2 grid gap-3 md:grid-cols-[1fr_auto]">
          <div>
            <label className="text-xs font-semibold uppercase text-slate/70">OTP</label>
            <input
              value={otpCode}
              onChange={(event) => setOtpCode(event.target.value)}
              className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
              placeholder="Enter 6-digit OTP"
              required
            />
          </div>
          <button
            type="button"
            onClick={handleRequestOtp}
            disabled={otpLoading}
            className="btn-outline self-end"
          >
            {otpLoading ? "Sending..." : otpSent ? "Resend OTP" : "Send OTP"}
          </button>
        </div>
        {otpInfo && <p className="text-xs text-slate/70 md:col-span-2">{otpInfo}</p>}
        {error && <p className="text-sm text-red-600 md:col-span-2">{error}</p>}
        {touched && (!form.username || !form.email || !form.password || !otpCode) && (
          <p className="text-xs text-slate/60 md:col-span-2">
            Fill in username, email, password and OTP.
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
