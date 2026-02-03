import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import api from "../api/client.js";

const GiveReview = () => {
  const location = useLocation();
  const tripFromQuery = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("trip") || "";
  }, [location.search]);

  const [form, setForm] = useState({
    trip: tripFromQuery,
    rating: 5,
    comment: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      setLoading(true);
      await api.post("/api/reviews/create/", form);
      setMessage("Review submitted.");
    } catch (err) {
      setError("Unable to submit review.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl rounded-3xl bg-white/90 p-8 shadow-glow">
      <h1 className="font-display text-3xl font-bold text-slate">Give a review</h1>
      <p className="mt-2 text-sm text-slate/70">
        Only riders who booked the trip can review it.
      </p>
      <form className="mt-6 grid gap-4" onSubmit={handleSubmit}>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Trip ID</label>
          <input
            name="trip"
            value={form.trip}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
            required
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Rating</label>
          <select
            name="rating"
            value={form.rating}
            onChange={handleChange}
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
          >
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold uppercase text-slate/70">Comment</label>
          <textarea
            name="comment"
            value={form.comment}
            onChange={handleChange}
            rows="4"
            className="mt-1 w-full rounded-xl border border-mist bg-white px-4 py-3"
          />
        </div>
        {message && <p className="text-sm text-emerald-600">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Submitting..." : "Submit review"}
        </button>
      </form>
    </div>
  );
};

export default GiveReview;
