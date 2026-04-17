import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib import error, request


logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
SEARCH_CONTEXT_FIELDS = (
    "source",
    "destination",
    "date",
    "seats_needed",
    "max_price",
    "time_preference",
    "sort_by",
)


class GeminiServiceError(Exception):
    pass


def call_gemini(prompt, temperature=0.3, max_output_tokens=250):
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise GeminiServiceError("GEMINI_API_KEY is not configured.")

    model_name = (os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "text/plain",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    gemini_request = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(gemini_request, timeout=20) as response:
            payload_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Gemini HTTP error %s: %s", exc.code, response_body)
        raise GeminiServiceError("Gemini request failed.") from exc
    except error.URLError as exc:
        logger.warning("Gemini network error: %s", exc)
        raise GeminiServiceError("Gemini is unavailable right now.") from exc

    try:
        payload_json = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned invalid JSON: %s", payload_text)
        raise GeminiServiceError("Gemini returned an unreadable response.") from exc

    candidates = payload_json.get("candidates") or []
    if not candidates:
        raise GeminiServiceError("Gemini returned no candidates.")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    text_response = "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    if not text_response:
        raise GeminiServiceError("Gemini returned an empty response.")

    return text_response


def extract_trip_details(message, history=None):
    recent_history = _normalize_history(history)
    prompt = f"""
You extract structured chatbot intent for RideMate.
Return valid JSON only with this exact shape:
{{
  "source": string or null,
  "destination": string or null,
  "date": "YYYY-MM-DD" or null,
  "intent": "find_ride" or "my_bookings" or "cancel_booking" or "book_ride" or "general",
  "follow_up_question": string or null,
  "seats_needed": integer or null,
  "max_price": number or null,
  "time_preference": "morning" or "afternoon" or "evening" or "night" or null,
  "sort_by": "cheapest" or "earliest" or "best_value" or null,
  "booking_reference": integer or null,
  "ride_reference": integer or null
}}

Rules:
- Use the recent conversation when the user asks follow-up questions.
- Convert relative dates like today or tomorrow into YYYY-MM-DD.
- If the user wants bookings, use "my_bookings".
- If the user wants to cancel a booking, use "cancel_booking".
- If the user wants to directly book a ride, use "book_ride".
- Keep missing fields as null.
- Return JSON only, with no markdown.

Recent conversation: {json.dumps(recent_history)}
User message: {json.dumps(message)}
""".strip()

    fallback = _merge_details_with_history(
        _fallback_extract_trip_details(message),
        recent_history,
    )
    try:
        raw_response = call_gemini(prompt, temperature=0.1, max_output_tokens=240)
        parsed = json.loads(_extract_json_block(raw_response))
    except (GeminiServiceError, json.JSONDecodeError, TypeError, ValueError):
        return fallback

    normalized = {
        "source": _normalize_place_name(parsed.get("source")) or fallback["source"],
        "destination": _normalize_place_name(parsed.get("destination")) or fallback["destination"],
        "date": _normalize_date_value(parsed.get("date")) or fallback["date"],
        "intent": _normalize_intent(parsed.get("intent"), message, fallback["intent"]),
        "follow_up_question": _normalize_text(parsed.get("follow_up_question")),
        "seats_needed": _normalize_seats_value(parsed.get("seats_needed")) or fallback["seats_needed"],
        "max_price": _normalize_price_value(parsed.get("max_price")) or fallback["max_price"],
        "time_preference": (
            _normalize_time_preference(parsed.get("time_preference")) or fallback["time_preference"]
        ),
        "sort_by": _normalize_sort_preference(parsed.get("sort_by")) or fallback["sort_by"],
        "booking_reference": (
            _normalize_reference(parsed.get("booking_reference")) or fallback["booking_reference"]
        ),
        "ride_reference": _normalize_reference(parsed.get("ride_reference")) or fallback["ride_reference"],
    }
    normalized = _merge_details_with_history(normalized, recent_history)
    if not normalized["follow_up_question"]:
        normalized["follow_up_question"] = _build_follow_up_question(normalized)
    return normalized


def generate_chatbot_reply(
    user_message,
    extracted_details,
    rides,
    bookings=None,
    history=None,
    recommendations=None,
    action_result=None,
):
    prompt = f"""
You are RideMate, a short and friendly assistant for ride search and booking help.

Instructions:
- Keep the response under 90 words.
- Use the recent conversation for context.
- If search details are incomplete, ask one helpful follow-up question.
- If rides exist, mention the best recommendation in plain language.
- If bookings exist, summarize them clearly.
- If an action_result exists, confirm the result naturally.
- Never invent rides, bookings, prices, seats, or IDs.
- Do not use markdown, bullet points, JSON, or tables.

Recent conversation: {json.dumps(_normalize_history(history))}
User message: {json.dumps(user_message)}
Extracted details: {json.dumps(extracted_details)}
Available rides: {json.dumps(rides)}
Bookings: {json.dumps(bookings or [])}
Recommendations: {json.dumps(recommendations or {})}
Action result: {json.dumps(action_result or {})}
""".strip()

    return call_gemini(prompt, temperature=0.35, max_output_tokens=170)


def build_fallback_reply(
    user_message,
    extracted_details,
    rides,
    bookings=None,
    recommendations=None,
    action_result=None,
):
    intent = extracted_details.get("intent")
    source = extracted_details.get("source")
    destination = extracted_details.get("destination")

    if action_result and action_result.get("type") == "cancel_booking":
        booking_id = action_result.get("booking_id")
        route = action_result.get("route") or "that booking"
        return f"Booking #{booking_id} for {route} has been canceled."

    if action_result and action_result.get("type") == "book_ride":
        trip_id = action_result.get("trip_id")
        route = action_result.get("route") or "that ride"
        remaining_seats = action_result.get("remaining_seats")
        return (
            f"Ride #{trip_id} for {route} is booked. "
            f"There are {remaining_seats} seat(s) left now."
        )

    if intent == "my_bookings":
        if bookings is None:
            return "Please login first, then I can show your bookings here."
        if not bookings:
            return "You do not have any active bookings right now."
        latest = bookings[0]
        trip = latest.get("trip_details") or {}
        route = f"{trip.get('source', 'Unknown')} to {trip.get('destination', 'Unknown')}"
        return (
            f"You have {len(bookings)} active booking(s). "
            f"Latest is booking #{latest['id']} for {route} on {trip.get('date', 'the scheduled date')}."
        )

    if intent == "cancel_booking":
        if bookings is None:
            return "Please login first, then I can cancel your booking."
        if extracted_details.get("booking_reference") is None:
            return "Tell me which booking to cancel, for example 'cancel booking 12'."
        return "I could not find that booking. Please check the booking number and try again."

    if intent == "book_ride":
        if not source and not destination and not extracted_details.get("ride_reference"):
            return "Tell me which ride to book, for example 'book ride 12' or search first."
        if rides:
            selected_ride = _pick_recommended_ride(rides, recommendations)
            if selected_ride:
                return (
                    f"I can book ride #{selected_ride['id']} from {selected_ride['source']} to "
                    f"{selected_ride['destination']} on {selected_ride['date']} at {selected_ride['time']} "
                    f"for Rs {selected_ride['price']}."
                )
        return "I could not find a matching ride to book right now."

    if not source and not destination:
        return extracted_details.get("follow_up_question") or (
            "Tell me your source and destination, and I will look for rides."
        )

    if rides:
        best_choice = _pick_recommended_ride(rides, recommendations)
        if best_choice:
            return (
                f"I found {len(rides)} ride(s). Best pick is ride #{best_choice['id']} from "
                f"{best_choice['source']} to {best_choice['destination']} on {best_choice['date']} "
                f"at {best_choice['time']} for Rs {best_choice['price']}."
            )
        cheapest = _pick_cheapest_ride(rides)
        return (
            f"I found {len(rides)} ride(s) for {source} to {destination}. "
            f"Cheapest is ride #{cheapest['id']} at Rs {cheapest['price']}."
        )

    price_hint = ""
    if extracted_details.get("max_price"):
        price_hint = f" under Rs {int(extracted_details['max_price'])}"
    if extracted_details.get("date"):
        return (
            f"I could not find a matching ride from {source or 'your source'} to "
            f"{destination or 'your destination'}{price_hint} on that date. "
            "Try another time or a nearby route."
        )

    return (
        f"I could not find a matching ride from {source or 'your source'} to "
        f"{destination or 'your destination'}{price_hint}. "
        "Try adding a date or changing the filters."
    )


def _fallback_extract_trip_details(message):
    cleaned_message = (message or "").strip()
    lowered_message = cleaned_message.lower()

    source = None
    destination = None
    patterns = [
        r"\bfrom\s+(?P<source>.+?)\s+to\s+(?P<destination>.+?)(?:\s+\b(?:on|for|at|under|before|after)\b|[?.!,]|$)",
        r"\bto\s+(?P<destination>.+?)\s+from\s+(?P<source>.+?)(?:\s+\b(?:on|for|at|under|before|after)\b|[?.!,]|$)",
        r"\b(?P<source>[A-Za-z][A-Za-z .-]{1,40})\s+to\s+(?P<destination>[A-Za-z][A-Za-z .-]{1,40})(?:\s+\b(?:on|for|at|under|before|after)\b|[?.!,]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned_message, flags=re.IGNORECASE)
        if not match:
            continue
        source = _normalize_place_name(match.group("source"))
        destination = _normalize_place_name(match.group("destination"))
        if source and destination:
            break

    parsed_date = _parse_date_from_message(cleaned_message)
    intent = _infer_intent(lowered_message, source, destination)
    return {
        "source": source,
        "destination": destination,
        "date": parsed_date,
        "intent": intent,
        "follow_up_question": None,
        "seats_needed": _extract_seat_count(cleaned_message),
        "max_price": _extract_max_price(cleaned_message),
        "time_preference": _extract_time_preference(cleaned_message),
        "sort_by": _extract_sort_preference(cleaned_message),
        "booking_reference": _extract_booking_reference(cleaned_message),
        "ride_reference": _extract_ride_reference(cleaned_message),
    }


def _merge_details_with_history(current, history):
    merged = dict(current)
    for previous_message in reversed(_history_user_messages(history)):
        previous = _fallback_extract_trip_details(previous_message)
        if previous.get("intent") in {"my_bookings", "cancel_booking"}:
            continue
        for field in SEARCH_CONTEXT_FIELDS:
            if not merged.get(field) and previous.get(field):
                merged[field] = previous[field]
        if merged.get("intent") == "general" and previous.get("intent") == "find_ride":
            merged["intent"] = "find_ride"
        if merged.get("source") and merged.get("destination") and merged.get("date"):
            break
    return merged


def _normalize_history(history):
    normalized = []
    if not isinstance(history, list):
        return normalized

    for entry in history[-8:]:
        if isinstance(entry, dict):
            role = "user" if entry.get("role") == "user" else "bot"
            text = _normalize_text(entry.get("text"))
            if text:
                normalized.append({"role": role, "text": text[:280]})
        elif isinstance(entry, str):
            text = _normalize_text(entry)
            if text:
                normalized.append({"role": "user", "text": text[:280]})
    return normalized


def _history_user_messages(history):
    return [
        entry.get("text", "")
        for entry in _normalize_history(history)
        if entry.get("role") == "user" and entry.get("text")
    ]


def _extract_json_block(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start : end + 1]


def _normalize_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_place_name(value):
    text = _normalize_text(value)
    if not text:
        return None

    text = re.sub(
        r"\b(please|ride|trip|available|book|booking|need|want|find|search|me|show|cancel)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(today|tomorrow|morning|afternoon|evening|night|day after tomorrow)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip(" ,.?")
    if not text:
        return None
    return text.title()


def _normalize_date_value(value):
    if not value:
        return None
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return _parse_date_from_message(text)


def _normalize_seats_value(value):
    try:
        seats = int(value)
    except (TypeError, ValueError):
        return None
    return seats if seats > 0 else None


def _normalize_price_value(value):
    if value in (None, ""):
        return None
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if normalized <= 0:
        return None
    return float(normalized)


def _normalize_time_preference(value):
    text = _normalize_text(value)
    if text in {"morning", "afternoon", "evening", "night"}:
        return text
    return None


def _normalize_sort_preference(value):
    text = _normalize_text(value)
    if text in {"cheapest", "earliest", "best_value"}:
        return text
    return None


def _normalize_reference(value):
    try:
        reference = int(value)
    except (TypeError, ValueError):
        return None
    return reference if reference > 0 else None


def _parse_date_from_message(message):
    lowered = (message or "").lower()
    today = date.today()

    if "day after tomorrow" in lowered:
        return (today + timedelta(days=2)).isoformat()
    if "tomorrow" in lowered:
        return (today + timedelta(days=1)).isoformat()
    if "today" in lowered:
        return today.isoformat()

    formats = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
    ]
    for pattern in formats:
        match = re.search(pattern, message or "")
        if not match:
            continue
        candidate = match.group(0)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                continue

    return None


def _extract_seat_count(message):
    match = re.search(r"\b(\d+)\s*(?:seat|seats|people|person)\b", message, flags=re.IGNORECASE)
    if match:
        return _normalize_seats_value(match.group(1))
    return None


def _extract_max_price(message):
    patterns = [
        r"\b(?:under|below|less than|within|budget(?: of)?|max(?:imum)?(?: price)?|upto|up to)\s*(?:rs\.?|inr)?\s*(\d+)\b",
        r"\b(?:rs\.?|inr)\s*(\d+)\s*(?:max|budget)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return _normalize_price_value(match.group(1))
    return None


def _extract_time_preference(message):
    lowered = (message or "").lower()
    for label in ("morning", "afternoon", "evening", "night"):
        if label in lowered:
            return label
    return None


def _extract_sort_preference(message):
    lowered = (message or "").lower()
    if any(keyword in lowered for keyword in ("cheapest", "cheap", "lowest price", "low price")):
        return "cheapest"
    if any(keyword in lowered for keyword in ("earliest", "first ride", "soonest")):
        return "earliest"
    if any(keyword in lowered for keyword in ("best value", "best option", "best ride", "recommended")):
        return "best_value"
    return None


def _extract_booking_reference(message):
    patterns = [
        r"\bbooking\s*#?\s*(\d+)\b",
        r"\bcancel\s*#?\s*(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return _normalize_reference(match.group(1))
    return None


def _extract_ride_reference(message):
    patterns = [
        r"\bride\s*#?\s*(\d+)\b",
        r"\btrip\s*#?\s*(\d+)\b",
        r"\bbook\s*#?\s*(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return _normalize_reference(match.group(1))
    return None


def _infer_intent(lowered_message, source, destination):
    if any(
        phrase in lowered_message
        for phrase in (
            "book ride",
            "book trip",
            "book cheapest",
            "book earliest",
            "book best",
            "join ride",
            "join trip",
        )
    ) or (
        lowered_message.startswith("book ")
        and "booking" not in lowered_message
    ):
        return "book_ride"
    if "cancel booking" in lowered_message or (
        "cancel" in lowered_message and "booking" in lowered_message
    ):
        return "cancel_booking"
    if any(
        keyword in lowered_message
        for keyword in ("my bookings", "my booking", "show bookings", "show my bookings")
    ):
        return "my_bookings"
    if any(
        keyword in lowered_message
        for keyword in ("booked rides", "confirmed rides", "reservation")
    ):
        return "my_bookings"
    if source or destination:
        return "find_ride"
    if any(keyword in lowered_message for keyword in ("ride", "trip", "travel", "go to")):
        return "find_ride"
    return "general"


def _normalize_intent(value, message, fallback_intent):
    intent = _normalize_text(value)
    if intent in {"find_ride", "my_bookings", "cancel_booking", "book_ride", "general"}:
        return intent
    inferred = _infer_intent((message or "").lower(), None, None)
    return inferred or fallback_intent


def _build_follow_up_question(details):
    if details.get("intent") == "book_ride" and not details.get("ride_reference"):
        if details.get("source") or details.get("destination"):
            return "I found the route context. Should I book the cheapest, earliest, or a specific ride ID?"
        return "Tell me which ride to book, for example 'book ride 12', or search for a route first."
    if details.get("intent") not in {"find_ride", "general"}:
        return None
    source = details.get("source")
    destination = details.get("destination")

    if not source and not destination:
        return "Tell me your source and destination, and I will look for rides."
    if not source:
        return "Where will you start your trip from?"
    if not destination:
        return "Where do you want to go?"
    return None


def _pick_cheapest_ride(rides):
    if not rides:
        return None
    return min(
        rides,
        key=lambda ride: (_parse_price(ride.get("price")), ride.get("date", ""), ride.get("time", "")),
    )


def _pick_earliest_ride(rides):
    if not rides:
        return None
    return min(
        rides,
        key=lambda ride: (ride.get("date", ""), ride.get("time", ""), _parse_price(ride.get("price"))),
    )


def _pick_best_value_ride(rides):
    if not rides:
        return None
    return min(
        rides,
        key=lambda ride: (
            _parse_price(ride.get("price")),
            -(ride.get("available_seats") or 0),
            ride.get("date", ""),
            ride.get("time", ""),
        ),
    )


def _pick_recommended_ride(rides, recommendations):
    if not rides:
        return None

    recommendations = recommendations or {}
    ride_by_id = {ride.get("id"): ride for ride in rides}
    for key in ("best_value", "cheapest", "earliest"):
        ride_id = recommendations.get(key)
        if ride_id in ride_by_id:
            return ride_by_id[ride_id]
    return rides[0]


def _parse_price(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("999999")
