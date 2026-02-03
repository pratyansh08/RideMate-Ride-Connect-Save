import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "../api/client.js";
import { isAuthed } from "../utils/auth.js";

const TripDetail = () => {
  const { id } = useParams();
  const [trip, setTrip] = useState(null);
  const [seats, setSeats] = useState(1);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchTrip = async () => {
      try {
        const response = await api.get(`/api/trips/${id}/`);
        setTrip(response.data);
      } catch (err) {
        setError("Trip not found.");
      }
    };
    fetchTrip();
  }, [id]);

  const handleBook = async () => {
    setMessage("");
    setError("");
    if (!isAuthed()) {
      setError("Please login to book.");
      return;
    }
    if (!seats || seats < 1) {
      setError("Seats must be at least 1.");
      return;
    }
    try {
      setLoading(true);
      const response = await api.post(`/api/trips/join/${id}/`, { seats });
      setTrip(response.data.trip);
      setMessage("Booking confirmed.");
    } catch (err) {
      setError("Booking failed. Check seats or login.");
    } finally {
      setLoading(false);
    }
  };

  if (!trip) {
    return <p className="text-sm text-slate/70">{error || "Loading..."}</p>;
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="rounded-3xl bg-white/90 p-8 shadow-glow">
        <p className="text-xs font-semibold uppercase text-slate/60">
          {trip.date} • {trip.time}
        </p>
        <h1 className="mt-2 font-display text-3xl font-bold text-slate">
          {trip.source} → {trip.destination}
        </h1>
        <p className="mt-3 text-sm text-slate/70">
          Seats available: {trip.available_seats}
        </p>
        <p className="text-sm text-slate/70">Price per seat: ₹{trip.price}</p>
        <div className="mt-6 flex items-center gap-3">
          <input
            type="number"
            min="1"
            value={seats}
            onChange={(event) => setSeats(Number(event.target.value))}
            className="w-24 rounded-xl border border-mist bg-white px-3 py-2"
          />
          <button
            type="button"
            onClick={handleBook}
            className="btn-primary"
            disabled={loading}
          >
            {loading ? "Booking..." : "Book seats"}
          </button>
        </div>
        {message && <p className="mt-3 text-sm text-emerald-600">{message}</p>}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
      <div className="rounded-3xl border border-mist bg-white/60 p-8">
        <h2 className="font-display text-2xl font-semibold text-slate">Reviews</h2>
        <p className="mt-2 text-sm text-slate/70">
          View or give feedback after your ride.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            to={`/reviews/trip?trip=${id}`}
            className="btn-outline"
          >
            View reviews
          </Link>
          <Link
            to={`/reviews/new?trip=${id}`}
            className="btn-primary"
          >
            Give review
          </Link>
          <Link to={`/chat/trip/${id}`} className="btn-outline">
            Open chat
          </Link>
        </div>
      </div>
    </div>
  );
};

export default TripDetail;
