import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "../api/client.js";

const PAGE_SIZE = 20;

const TripChat = () => {
  const { id } = useParams();
  const tripId = useMemo(() => Number(id), [id]);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState("");
  const [attachment, setAttachment] = useState(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadMessages = async (nextOffset = 0, append = false) => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get(
        `/api/chat/trip/${tripId}/?limit=${PAGE_SIZE}&offset=${nextOffset}`,
      );
      const incoming = response.data || [];
      setMessages((prev) => (append ? [...prev, ...incoming] : incoming));
      setHasMore(incoming.length === PAGE_SIZE);
    } catch (err) {
      setError("Unable to load chat messages.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (Number.isNaN(tripId)) return;
    setOffset(0);
    loadMessages(0, false);
  }, [tripId]);

  const handleSend = async (event) => {
    event.preventDefault();
    setError("");
    setSending(true);
    try {
      const formData = new FormData();
      formData.append("trip", String(tripId));
      if (message) formData.append("message", message);
      if (attachment) formData.append("attachment", attachment);
      await api.post("/api/chat/send/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage("");
      setAttachment(null);
      setOffset(0);
      await loadMessages(0, false);
    } catch (err) {
      setError("Unable to send message.");
    } finally {
      setSending(false);
    }
  };

  const handleLoadMore = () => {
    const nextOffset = offset + PAGE_SIZE;
    setOffset(nextOffset);
    loadMessages(nextOffset, true);
  };

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold text-slate">Trip Chat</h1>
          <p className="text-sm text-slate/70">Trip ID: {tripId}</p>
        </div>
        <Link to={`/trips/${tripId}`} className="btn-outline">
          Back to trip
        </Link>
      </div>

      <div className="rounded-3xl border border-mist bg-white/80 p-6">
        <div className="grid gap-4">
          {messages.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-mist bg-white px-4 py-3"
            >
              <p className="text-xs font-semibold uppercase text-slate/60">
                User {item.sender} • {new Date(item.created_at).toLocaleString()}
              </p>
              {item.message && <p className="mt-2 text-sm text-slate">{item.message}</p>}
              {item.attachment_url && (
                <a
                  href={item.attachment_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-sm font-semibold text-emerald-700"
                >
                  View attachment
                </a>
              )}
            </div>
          ))}
          {messages.length === 0 && !loading && (
            <div className="rounded-2xl border border-dashed border-mist bg-white/60 p-6 text-center text-sm text-slate/70">
              No messages yet.
            </div>
          )}
        </div>
        {hasMore && (
          <button
            type="button"
            onClick={handleLoadMore}
            className="btn-outline mt-4 w-full"
            disabled={loading}
          >
            {loading ? "Loading..." : "Load more"}
          </button>
        )}
      </div>

      <form
        onSubmit={handleSend}
        className="rounded-3xl bg-white/90 p-6 shadow-glow"
      >
        <h2 className="font-display text-2xl font-semibold text-slate">Send message</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Type your message"
            rows="4"
            className="w-full rounded-xl border border-mist bg-white px-4 py-3 md:col-span-2"
          />
          <input
            type="file"
            onChange={(event) => setAttachment(event.target.files?.[0] || null)}
            className="w-full rounded-xl border border-mist bg-white px-4 py-3"
          />
          <button type="submit" className="btn-primary" disabled={sending}>
            {sending ? "Sending..." : "Send"}
          </button>
        </div>
        {!message && !attachment && (
          <p className="mt-3 text-xs text-slate/60">
            Add a message or an attachment to send.
          </p>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </form>
    </div>
  );
};

export default TripChat;
