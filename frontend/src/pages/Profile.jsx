import { useEffect, useState } from "react";

import api from "../api/client.js";

const Profile = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ phone: "", gender: "" });
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    const loadProfile = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await api.get("/api/accounts/me/");
        setProfile(response.data);
        setForm({
          phone: response.data.phone || "",
          gender: response.data.gender || "",
        });
      } catch (err) {
        const detail = err?.response?.data?.detail;
        setError(detail || "Unable to load profile right now.");
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setSaveMessage("");
    setError("");
    setSaving(true);
    try {
      const response = await api.patch("/api/accounts/me/", form);
      setProfile(response.data);
      setForm({
        phone: response.data.phone || "",
        gender: response.data.gender || "",
      });
      setSaveMessage("Profile updated successfully.");
    } catch (err) {
      const phoneErr = err?.response?.data?.phone?.[0];
      const genderErr = err?.response?.data?.gender?.[0];
      const detail = err?.response?.data?.detail;
      setError(phoneErr || genderErr || detail || "Unable to update profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-[28px] border border-mist bg-white p-8">
      <h1 className="font-display text-3xl font-bold text-slate">
        {profile ? `Welcome, ${profile.username}` : "Welcome"}
      </h1>
      <p className="mt-2 text-sm text-slate/70">
        This is your profile section. Your account details are shown here after login.
      </p>

      {loading && <p className="mt-6 text-sm text-slate/60">Loading your profile...</p>}
      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}

      {!loading && !error && profile && (
        <div className="mt-6 grid gap-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl bg-fog p-4">
              <p className="text-xs uppercase text-slate/60">Username</p>
              <p className="mt-1 text-sm font-semibold text-slate">{profile.username || "-"}</p>
            </div>
            <div className="rounded-2xl bg-fog p-4">
              <p className="text-xs uppercase text-slate/60">Email</p>
              <p className="mt-1 text-sm font-semibold text-slate">{profile.email || "-"}</p>
            </div>
            <div className="rounded-2xl bg-fog p-4">
              <p className="text-xs uppercase text-slate/60">Rating</p>
              <p className="mt-1 text-sm font-semibold text-slate">{profile.rating ?? 0}</p>
            </div>
            <div className="rounded-2xl bg-fog p-4">
              <p className="text-xs uppercase text-slate/60">Ratings Count</p>
              <p className="mt-1 text-sm font-semibold text-slate">{profile.rating_count ?? 0}</p>
            </div>
          </div>

          <form onSubmit={handleSave} className="rounded-2xl border border-mist bg-fog p-4">
            <h2 className="text-sm font-semibold text-slate">Edit Profile Details</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs uppercase text-slate/60">Phone</label>
                <input
                  name="phone"
                  value={form.phone}
                  onChange={handleChange}
                  className="mt-2 w-full rounded-xl border border-mist bg-white px-3 py-2 text-sm"
                  placeholder="Enter phone number"
                />
              </div>
              <div>
                <label className="text-xs uppercase text-slate/60">Gender</label>
                <select
                  name="gender"
                  value={form.gender}
                  onChange={handleChange}
                  className="mt-2 w-full rounded-xl border border-mist bg-white px-3 py-2 text-sm"
                >
                  <option value="">Select gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            {saveMessage && <p className="mt-3 text-sm text-lime">{saveMessage}</p>}
            <button type="submit" disabled={saving} className="btn-primary mt-4">
              {saving ? "Saving..." : "Save Profile"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
};

export default Profile;
