import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "../api/client.js";

const MyBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  useEffect(() => {
    const fetchBookings = async () => {
      try {
        setLoading(true);
        const response = await api.get("/api/trips/my-bookings/");
        setBookings(response.data);
      } catch (err) {
        setError("Unable to load bookings.");
      } finally {
        setLoading(false);
      }
    };
    fetchBookings();
  }, []);

  const handleCancel = async (bookingId) => {
    setActionMessage("");
    setError("");
    try {
      await api.post(`/api/trips/bookings/${bookingId}/cancel/`);
      setBookings((prev) => prev.filter((b) => b.id !== bookingId));
      setActionMessage("Booking cancelled.");
    } catch (err) {
      setError("Unable to cancel booking.");
    }
  };

  return (
    <div className="grid gap-4">
      <h1 className="font-display text-3xl font-bold text-slate">My Bookings</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {actionMessage && <p className="text-sm text-emerald-600">{actionMessage}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {bookings.map((booking) => (
          <div
            key={booking.id}
            className="rounded-3xl border border-mist bg-white/80 p-6"
          >
            <Link to={`/trips/${booking.trip}`}>
              <p className="text-xs font-semibold uppercase text-slate/60">
                Booking #{booking.id}
              </p>
              <p className="mt-2 text-sm text-slate/70">
                Trip ID: {booking.trip} • Seats: {booking.seats}
              </p>
              <p className="text-xs text-slate/60">Created: {booking.created_at}</p>
            </Link>
            <button
              type="button"
              onClick={() => handleCancel(booking.id)}
              className="btn-outline mt-4"
            >
              Cancel booking
            </button>
          </div>
        ))}
        {bookings.length === 0 && !loading && (
          <div className="rounded-3xl border border-dashed border-mist bg-white/60 p-8 text-center text-sm text-slate/70 md:col-span-2">
            You have no bookings yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default MyBookings;
