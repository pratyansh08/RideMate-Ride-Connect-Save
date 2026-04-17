import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getToken, isAuthed } from "../utils/auth.js";


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const STORAGE_KEY = "ridemate-ai-chat-v2";

const QUICK_ACTIONS = [
  { id: "find-ride", label: "Find Ride", message: "Find me a ride" },
  { id: "my-bookings", label: "My Bookings", message: "Show my bookings" },
];

const createMessage = (role, text, options = {}) => ({
  id: options.id || `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  role,
  text,
  rides: options.rides || [],
  bookings: options.bookings || [],
  suggestions: options.suggestions || [],
  recommendations: options.recommendations || {},
  context: options.context || {},
});

const INITIAL_MESSAGES = [
  createMessage(
    "bot",
    "Hi, I am your RideMate assistant. Ask for rides, compare options, book by text, or check your bookings.",
    {
      suggestions: [
        "Find me a ride from Pune to Mumbai tomorrow",
        "Book cheapest ride",
        "Show my bookings",
      ],
    },
  ),
];

const readJsonResponse = async (response) => {
  try {
    return await response.json();
  } catch (error) {
    return {};
  }
};

const loadStoredMessages = () => {
  if (typeof window === "undefined") {
    return INITIAL_MESSAGES;
  }

  try {
    const rawValue = window.localStorage.getItem(STORAGE_KEY);
    if (!rawValue) {
      return INITIAL_MESSAGES;
    }
    const parsed = JSON.parse(rawValue);
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return INITIAL_MESSAGES;
    }
    return parsed.map((item) =>
      createMessage(item.role === "user" ? "user" : "bot", item.text || "", {
        id: item.id,
        rides: Array.isArray(item.rides) ? item.rides : [],
        bookings: Array.isArray(item.bookings) ? item.bookings : [],
        suggestions: Array.isArray(item.suggestions) ? item.suggestions : [],
        recommendations: item.recommendations || {},
        context: item.context || {},
      }),
    );
  } catch (error) {
    return INITIAL_MESSAGES;
  }
};

const buildHistoryPayload = (messages) =>
  messages
    .filter((item) => item.text)
    .slice(-8)
    .map((item) => ({ role: item.role, text: item.text }));

const getRideBadges = (recommendations, rideId) => {
  const badges = [];
  if (recommendations?.cheapest === rideId) {
    badges.push("Cheapest");
  }
  if (recommendations?.earliest === rideId) {
    badges.push("Earliest");
  }
  if (recommendations?.best_value === rideId) {
    badges.push("Best Value");
  }
  return badges;
};

const Chat = ({ embedded = false, onClose, onOpenFull }) => {
  const navigate = useNavigate();
  const endOfMessagesRef = useRef(null);
  const [messages, setMessages] = useState(() => loadStoredMessages());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [bookingTripId, setBookingTripId] = useState(null);
  const [cancellingBookingId, setCancellingBookingId] = useState(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const sendMessage = async (rawMessage) => {
    const message = rawMessage.trim();
    if (!message || loading) {
      return;
    }

    setError("");
    setInput("");
    const userMessage = createMessage("user", message);
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE_URL}/api/chatbot/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message,
          history: buildHistoryPayload(nextMessages),
        }),
      });
      const data = await readJsonResponse(response);
      if (!response.ok) {
        throw new Error(data.detail || "Unable to reach the RideMate assistant.");
      }

      setMessages((prev) => [
        ...prev,
        createMessage("bot", data.reply || "I could not generate a reply right now.", {
          rides: Array.isArray(data.rides) ? data.rides : [],
          bookings: Array.isArray(data.bookings) ? data.bookings : [],
          suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
          recommendations: data.recommendations || {},
          context: data.context || {},
        }),
      ]);
    } catch (requestError) {
      const errorMessage =
        requestError.message || "Unable to reach the RideMate assistant right now.";
      setError(errorMessage);
      setMessages((prev) => [
        ...prev,
        createMessage("bot", "I am having trouble right now. Please try again in a moment."),
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await sendMessage(input);
  };

  const handleQuickAction = async (action) => {
    await sendMessage(action.message);
  };

  const handleNewChat = () => {
    setMessages(INITIAL_MESSAGES);
    setInput("");
    setError("");
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  };

  const handleBookRide = async (ride) => {
    if (!isAuthed()) {
      setMessages((prev) => [
        ...prev,
        createMessage("bot", "Please login to book this ride."),
      ]);
      navigate("/login");
      return;
    }

    setError("");
    setBookingTripId(ride.id);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE_URL}/api/trips/${ride.id}/book/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ seats: 1 }),
      });
      const data = await readJsonResponse(response);
      if (!response.ok) {
        throw new Error(data.detail || "Booking failed. Please try again.");
      }

      const updatedTrip = data.trip || ride;
      setMessages((prev) => {
        const updatedMessages = prev.map((item) => ({
          ...item,
          rides: (item.rides || []).map((entry) =>
            entry.id === updatedTrip.id ? { ...entry, ...updatedTrip } : entry,
          ),
        }));
        return [
          ...updatedMessages,
          createMessage(
            "bot",
            `Booked! ${updatedTrip.source} to ${updatedTrip.destination} now has ${updatedTrip.available_seats} seat(s) left.`,
            {
              suggestions: ["Show my bookings", "Find return ride"],
            },
          ),
        ];
      });
    } catch (requestError) {
      const errorMessage = requestError.message || "Booking failed. Please try again.";
      setError(errorMessage);
      setMessages((prev) => [...prev, createMessage("bot", errorMessage)]);
    } finally {
      setBookingTripId(null);
    }
  };

  const handleCancelBooking = async (booking) => {
    if (!isAuthed()) {
      setMessages((prev) => [
        ...prev,
        createMessage("bot", "Please login first, then I can cancel this booking."),
      ]);
      navigate("/login");
      return;
    }

    setError("");
    setCancellingBookingId(booking.id);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE_URL}/api/trips/bookings/${booking.id}/cancel/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      const data = await readJsonResponse(response);
      if (!response.ok) {
        throw new Error(data.detail || "Unable to cancel booking.");
      }

      const trip = booking.trip_details || {};
      setMessages((prev) => {
        const updatedMessages = prev.map((item) => ({
          ...item,
          bookings: (item.bookings || []).filter((entry) => entry.id !== booking.id),
        }));
        return [
          ...updatedMessages,
          createMessage(
            "bot",
            `Booking #${booking.id} for ${trip.source || "your trip"} to ${trip.destination || ""} has been canceled.`,
            {
              suggestions: ["Find me a ride", "Show my bookings"],
            },
          ),
        ];
      });
    } catch (requestError) {
      const errorMessage = requestError.message || "Unable to cancel booking.";
      setError(errorMessage);
      setMessages((prev) => [...prev, createMessage("bot", errorMessage)]);
    } finally {
      setCancellingBookingId(null);
    }
  };

  const wrapperClass = embedded
    ? "flex h-full max-h-[calc(100vh-5rem)] flex-col gap-0"
    : "mx-auto grid w-full max-w-5xl gap-5";
  const heroCardClass = embedded
    ? "border-b border-white/15 bg-ink px-3 py-3 text-white"
    : "rounded-3xl bg-white/90 p-5 shadow-glow";
  const shellClass = embedded
    ? "flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.5rem] border border-ink/10 bg-white shadow-2xl"
    : "overflow-hidden rounded-[2rem] border border-mist bg-white/90 shadow-glow";
  const messagePanelClass = embedded
    ? "min-h-0 flex-1 overflow-y-auto bg-fog/60 px-3 py-3"
    : "h-[31rem] overflow-y-auto bg-fog/60 px-4 py-4 sm:px-5";
  const formClass = embedded
    ? "border-t border-mist bg-white px-3 py-3"
    : "border-t border-mist bg-white px-4 py-3 sm:px-5";

  return (
    <div className={wrapperClass}>
      <div className={heroCardClass}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p
              className={`text-xs font-semibold uppercase tracking-[0.3em] ${
                embedded ? "text-white/60" : "text-slate/50"
              }`}
            >
              AI Assistant
            </p>
            <h1
              className={`mt-2 font-display font-bold ${
                embedded ? "text-xl text-white" : "text-3xl text-slate"
              }`}
            >
              RideMate Chat
            </h1>
            <p
              className={`mt-2 max-w-2xl text-sm ${
                embedded ? "text-white/75" : "text-slate/70"
              }`}
            >
              {embedded
                ? "Ask, compare, book, or cancel right from here."
                : "Ask naturally, keep the conversation going, check bookings, book rides by text, or cancel one without leaving the chat."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.id}
                type="button"
                onClick={() => handleQuickAction(action)}
                className={embedded ? "btn-soft" : "btn-outline"}
                disabled={loading}
              >
                {action.label}
              </button>
            ))}
            <button type="button" onClick={handleNewChat} className={embedded ? "btn-soft" : "btn-outline"}>
              New Chat
            </button>
            {embedded && onOpenFull && (
              <button type="button" onClick={onOpenFull} className="btn-soft">
                Open Full
              </button>
            )}
            {embedded && onClose && (
              <button type="button" onClick={onClose} className="btn-soft">
                Close
              </button>
            )}
          </div>
        </div>
      </div>

      <div className={shellClass}>
        <div className={messagePanelClass}>
          <div className="grid gap-4">
            {messages.map((item) => {
              const isUser = item.role === "user";
              return (
                <div key={item.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[92%] rounded-[1.5rem] px-4 py-3 shadow-sm ${
                      isUser
                        ? "rounded-br-md bg-ink text-white"
                        : "rounded-bl-md border border-mist bg-white text-slate"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-6">{item.text}</p>

                    {item.rides?.length > 0 && (
                      <div className="mt-4 grid gap-3">
                        {item.rides.map((ride) => {
                          const badges = getRideBadges(item.recommendations, ride.id);
                          return (
                            <div
                              key={ride.id}
                              className="rounded-2xl border border-mist bg-fog px-4 py-4 text-slate"
                            >
                              {badges.length > 0 && (
                                <div className="mb-3 flex flex-wrap gap-2">
                                  {badges.map((badge) => (
                                    <span
                                      key={`${ride.id}-${badge}`}
                                      className="rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white"
                                    >
                                      {badge}
                                    </span>
                                  ))}
                                </div>
                              )}
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate/55">
                                {ride.date} at {ride.time}
                              </p>
                              <h2 className="mt-2 text-lg font-semibold">
                                {ride.source} -&gt; {ride.destination}
                              </h2>
                              <p className="mt-2 text-sm text-slate/75">
                                Price: Rs {ride.price} | Seats: {ride.available_seats}
                              </p>
                              <div className="mt-4 flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  className="btn-primary"
                                  onClick={() => handleBookRide(ride)}
                                  disabled={bookingTripId === ride.id || ride.available_seats < 1}
                                >
                                  {bookingTripId === ride.id ? "Booking..." : "Book"}
                                </button>
                                <Link to={`/trips/${ride.id}`} className="btn-outline">
                                  View Trip
                                </Link>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {item.bookings?.length > 0 && (
                      <div className="mt-4 grid gap-3">
                        {item.bookings.map((booking) => {
                          const trip = booking.trip_details || {};
                          return (
                            <div
                              key={booking.id}
                              className="rounded-2xl border border-mist bg-fog px-4 py-4 text-slate"
                            >
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate/55">
                                Booking #{booking.id}
                              </p>
                              <h2 className="mt-2 text-lg font-semibold">
                                {trip.source || "Unknown"} -&gt; {trip.destination || "Unknown"}
                              </h2>
                              <p className="mt-2 text-sm text-slate/75">
                                {trip.date || "No date"} at {trip.time || "No time"} | Seats: {booking.seats}
                              </p>
                              <p className="mt-1 text-sm text-slate/75">
                                Price: Rs {trip.price || "N/A"} | Driver: {booking.driver_name || "N/A"}
                              </p>
                              <div className="mt-4 flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  className="btn-outline"
                                  onClick={() => handleCancelBooking(booking)}
                                  disabled={cancellingBookingId === booking.id}
                                >
                                  {cancellingBookingId === booking.id ? "Cancelling..." : "Cancel Booking"}
                                </button>
                                <Link to={`/trips/${booking.trip}`} className="btn-primary">
                                  View Trip
                                </Link>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {item.suggestions?.length > 0 && !isUser && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {item.suggestions.map((suggestion) => (
                          <button
                            key={`${item.id}-${suggestion}`}
                            type="button"
                            onClick={() => sendMessage(suggestion)}
                            className="rounded-full border border-mist bg-white px-3 py-2 text-xs font-semibold text-slate transition hover:border-ink hover:text-ink"
                            disabled={loading}
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {loading && (
              <div className="flex justify-start">
                <div className="max-w-[18rem] rounded-[1.5rem] rounded-bl-md border border-mist bg-white px-4 py-3 text-sm text-slate/70 shadow-sm">
                  RideMate is checking rides, bookings, reviews, and next best options...
                </div>
              </div>
            )}
            <div ref={endOfMessagesRef} />
          </div>
        </div>

        <form onSubmit={handleSubmit} className={formClass}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex-1">
              <span className="sr-only">Type your message</span>
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Try: 'book cheapest ride under 500 tomorrow morning'"
                rows="2"
                className={`w-full rounded-2xl border border-mist bg-fog text-sm text-slate outline-none transition focus:border-ink ${
                  embedded ? "min-h-20 px-3 py-2.5" : "min-h-20 px-4 py-2.5"
                }`}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    handleSubmit(event);
                  }
                }}
              />
            </label>
            <button
              type="submit"
              className="btn-primary sm:min-w-32"
              disabled={loading || !input.trim()}
            >
              {loading ? "Sending..." : "Send"}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </form>
      </div>
    </div>
  );
};

export default Chat;
