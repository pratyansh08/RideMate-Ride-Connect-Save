import { useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client.js";

const CreateTrip = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    source: "",
    destination: "",
    date: "",
    time: "",
    available_seats: 1,
    price: "",
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
    if (!form.source || !form.destination || !form.date || !form.time || !form.price) {
      setError("All fields are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await api.post("/api/trips/create/", form);
      navigate(`/trips/${response.data.id}`);
    } catch (err) {
      setError("Trip creation failed. Check inputs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl rounded-3xl bg-white/90 p-8 shadow-glow">
      <h1 className="font-display text-3xl font-bold text-slate">Create a trip</h1>
      <p className="mt-2 text-sm text-slate/70">
        Share your route and earn by offering seats.
      </p>
      <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">From</label>
          <input
            name="source"
            value={form.source}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">To</label>
          <input
            name="destination"
            value={form.destination}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Date</label>
          <input
            type="date"
            name="date"
            value={form.date}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Time</label>
          <input
            type="time"
            name="time"
            value={form.time}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Seats</label>
          <input
            type="number"
            min="1"
            name="available_seats"
            value={form.available_seats}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Price</label>
          <input
            type="number"
            step="0.01"
            name="price"
            value={form.price}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        {error && <p className="text-sm text-red-600 md:col-span-2">{error}</p>}
        {touched &&
          (!form.source ||
            !form.destination ||
            !form.date ||
            !form.time ||
            !form.price) && (
            <p className="text-xs text-slate/60 md:col-span-2">
              Please fill all fields before submitting.
            </p>
          )}
        <button type="submit" disabled={loading} className="btn-primary md:col-span-2">
          {loading ? "Creating..." : "Create trip"}
        </button>
      </form>
    </div>
  );
};

export default CreateTrip;
