import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "../api/client.js";

const MyTrips = () => {
  const [trips, setTrips] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchTrips = async () => {
      try {
        const response = await api.get("/api/trips/my/");
        setTrips(response.data);
      } catch (err) {
        setError("Unable to load trips.");
      }
    };
    fetchTrips();
  }, []);

  return (
    <div className="grid gap-4">
      <h1 className="font-display text-3xl font-bold text-slate">My Trips</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {trips.map((trip) => (
          <Link
            key={trip.id}
            to={`/trips/${trip.id}`}
            className="rounded-3xl border border-mist bg-white/80 p-6"
          >
            <p className="text-xs font-semibold uppercase text-slate/60">
              {trip.date} • {trip.time}
            </p>
            <h2 className="mt-2 text-xl font-semibold text-slate">
              {trip.source} → {trip.destination}
            </h2>
            <p className="mt-2 text-sm text-slate/70">
              Seats: {trip.available_seats} • ₹{trip.price}
            </p>
          </Link>
        ))}
        {trips.length === 0 && (
          <div className="rounded-3xl border border-dashed border-mist bg-white/60 p-8 text-center text-sm text-slate/70 md:col-span-2">
            You have not created any trips yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default MyTrips;
