import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import api from "../api/client.js";
import { isAuthed } from "../utils/auth.js";


const TripReviews = () => {
  const location = useLocation();
  const tripFromQuery = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("trip") || "";
  }, [location.search]);

  const [tripId, setTripId] = useState(tripFromQuery);
  const [reviews, setReviews] = useState([]);
  const [summary, setSummary] = useState("");
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchReviews = async () => {
    if (!tripId) return;
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const [reviewsResponse, summaryResponse] = await Promise.all([
        api.get(`/api/reviews/trip/${tripId}/`),
        api.get(`/api/reviews/trip/${tripId}/summary/`),
      ]);
      setReviews(reviewsResponse.data);
      setSummary(summaryResponse.data.summary || "");
      setStats(summaryResponse.data.stats || null);
    } catch (err) {
      setError("Unable to load reviews.");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (reviewId, currentRating, currentComment) => {
    const rating = window.prompt("New rating (1-5):", String(currentRating));
    if (!rating) return;
    const comment = window.prompt("New comment:", currentComment || "");
    try {
      await api.patch(`/api/reviews/${reviewId}/`, {
        rating: Number(rating),
        comment,
        trip: tripId,
      });
      setMessage("Review updated.");
      fetchReviews();
    } catch (err) {
      setError("Unable to update review.");
    }
  };

  const handleDelete = async (reviewId) => {
    if (!window.confirm("Delete this review?")) return;
    try {
      await api.delete(`/api/reviews/${reviewId}/`);
      setMessage("Review deleted.");
      setReviews((prev) => prev.filter((review) => review.id !== reviewId));
      fetchReviews();
    } catch (err) {
      setError("Unable to delete review.");
    }
  };

  return (
    <div className="grid gap-6">
      <div className="rounded-3xl bg-white/90 p-8 shadow-glow">
        <h1 className="font-display text-3xl font-bold text-slate">Trip reviews</h1>
        <div className="mt-4 flex flex-wrap gap-3">
          <input
            value={tripId}
            onChange={(event) => setTripId(event.target.value)}
            placeholder="Trip ID"
            className="rounded-xl border border-mist bg-white px-4 py-3"
          />
          <button type="button" onClick={fetchReviews} className="btn-primary" disabled={loading}>
            {loading ? "Loading..." : "Fetch reviews"}
          </button>
        </div>
        {message && <p className="mt-3 text-sm text-emerald-600">{message}</p>}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      {(summary || stats) && (
        <div className="grid gap-4 md:grid-cols-[1.6fr_1fr]">
          <div className="rounded-3xl border border-mist bg-white/90 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate/50">
              AI Summary
            </p>
            <p className="mt-3 text-sm leading-7 text-slate/75">{summary}</p>
          </div>
          <div className="rounded-3xl border border-mist bg-white/90 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate/50">
              Snapshot
            </p>
            <div className="mt-4 grid gap-3 text-sm text-slate/75">
              <p>Total reviews: {stats?.count ?? 0}</p>
              <p>Average rating: {stats?.average_rating ?? 0}</p>
              <p>Positive reviews: {stats?.positive_reviews ?? 0}</p>
              <p>Critical reviews: {stats?.critical_reviews ?? 0}</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {reviews.map((review) => (
          <div key={review.id} className="rounded-3xl border border-mist bg-white/80 p-6">
            <p className="text-xs font-semibold uppercase text-slate/60">
              Rating: {review.rating} / 5
            </p>
            <p className="mt-2 text-sm text-slate/70">{review.comment || "No comment."}</p>
            <p className="mt-3 text-xs text-slate/60">Reviewer: {review.reviewer}</p>
            {isAuthed() && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleUpdate(review.id, review.rating, review.comment)}
                  className="btn-outline"
                >
                  Update
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(review.id)}
                  className="btn-outline"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        ))}
        {reviews.length === 0 && !loading && (
          <div className="rounded-3xl border border-dashed border-mist bg-white/60 p-8 text-center text-sm text-slate/70 md:col-span-2">
            No reviews yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default TripReviews;
