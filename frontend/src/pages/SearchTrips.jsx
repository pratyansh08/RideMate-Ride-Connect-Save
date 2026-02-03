import { useState } from "react";
import { Link } from "react-router-dom";

import api from "../api/client.js";

const SearchTrips = () => {
  const [filters, setFilters] = useState({
    from: "",
    to: "",
    date: "",
    min_price: "",
    max_price: "",
    seats: "",
    time: "",
  });
  const [trips, setTrips] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);

  const handleChange = (event) => {
    setFilters((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSearch = async (event) => {
    event.preventDefault();
    setTouched(true);
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (filters.from) params.append("from", filters.from);
      if (filters.to) params.append("to", filters.to);
      if (filters.date) params.append("date", filters.date);
      if (filters.min_price) params.append("min_price", filters.min_price);
      if (filters.max_price) params.append("max_price", filters.max_price);
      if (filters.seats) params.append("seats", filters.seats);
      if (filters.time) params.append("time", filters.time);
      const response = await api.get(`/api/trips/search/?${params.toString()}`);
      setTrips(response.data);
    } catch (err) {
      setError("Search failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div className="rounded-3xl bg-white/90 p-8 shadow-glow">
        <h1 className="font-display text-3xl font-bold text-slate">Find a ride</h1>
        <form className="mt-6 grid gap-4 md:grid-cols-4" onSubmit={handleSearch}>
          <input
            name="from"
            value={filters.from}
            onChange={handleChange}
            placeholder="From"
            className="rounded-xl border border-mist bg-white px-4 py-3"
          />
          <input
            name="to"
            value={filters.to}
            onChange={handleChange}
            placeholder="To"
            className="rounded-xl border border-mist bg-white px-4 py-3"
          />
          <input
            type="date"
            name="date"
            value={filters.date}
            onChange={handleChange}
            className="rounded-xl border border-mist bg-white px-4 py-3"
          />
          <input
            type="time"
            name="time"
            value={filters.time}
            onChange={handleChange}
            className="rounded-xl border border-mist bg-white px-4 py-3"
          />
          <input
            type="number"
            name="min_price"
            value={filters.min_price}
            onChange={handleChange}
            className="rounded-xl border border-mist bg-white px-4 py-3"
            placeholder="Min price"
          />
          <input
            type="number"
            name="max_price"
            value={filters.max_price}
            onChange={handleChange}
            className="rounded-xl border border-mist bg-white px-4 py-3"
            placeholder="Max price"
          />
          <input
            type="number"
            name="seats"
            value={filters.seats}
            onChange={handleChange}
            className="rounded-xl border border-mist bg-white px-4 py-3"
            placeholder="Min seats"
          />
          <button type="submit" className="btn-primary">
            {loading ? "Searching..." : "Search"}
          </button>
        </form>
        {touched && !filters.from && !filters.to && !filters.date && (
          <p className="mt-3 text-xs text-slate/60">
            Add at least one filter to get better results.
          </p>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {trips.map((trip) => (
          <Link
            key={trip.id}
            to={`/trips/${trip.id}`}
            className="rounded-3xl border border-mist bg-white/80 p-6 transition hover:-translate-y-1 hover:shadow-glow"
          >
            <p className="text-xs font-semibold uppercase text-slate/60">
              {trip.date} • {trip.time}
            </p>
            <h2 className="mt-2 text-xl font-semibold text-slate">
              {trip.source} → {trip.destination}
            </h2>
            <p className="mt-2 text-sm text-slate/70">
              Seats: {trip.available_seats} • Price: ₹{trip.price}
            </p>
          </Link>
        ))}
        {trips.length === 0 && !loading && (
          <div className="rounded-3xl border border-dashed border-mist bg-white/60 p-8 text-center text-sm text-slate/70 md:col-span-2">
            No trips yet. Try a new search.
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchTrips;
