import json

from chat.ai_service import GeminiServiceError, call_gemini


def summarize_trip_reviews(trip_id, reviews):
    normalized_reviews = [
        {
            "rating": review.get("rating"),
            "comment": (review.get("comment") or "").strip(),
            "reviewer": review.get("reviewer"),
        }
        for review in reviews
    ]

    if not normalized_reviews:
        return {
            "summary": "No reviews yet for this trip.",
            "stats": {
                "count": 0,
                "average_rating": 0,
                "positive_reviews": 0,
                "critical_reviews": 0,
            },
        }

    stats = _build_review_stats(normalized_reviews)
    prompt = f"""
You summarize RideMate trip reviews in a short, balanced way.

Rules:
- Keep the summary under 70 words.
- Mention overall sentiment and one or two notable patterns.
- Be specific but do not invent facts.
- Do not use markdown, bullets, or JSON in the summary text.

Trip ID: {trip_id}
Review stats: {json.dumps(stats)}
Reviews: {json.dumps(normalized_reviews)}
""".strip()

    try:
        summary = call_gemini(prompt, temperature=0.2, max_output_tokens=120)
    except GeminiServiceError:
        summary = _build_fallback_summary(stats, normalized_reviews)

    return {
        "summary": summary,
        "stats": stats,
    }


def _build_review_stats(reviews):
    count = len(reviews)
    total = sum(int(review.get("rating") or 0) for review in reviews)
    average_rating = round(total / count, 2) if count else 0
    positive_reviews = sum(1 for review in reviews if int(review.get("rating") or 0) >= 4)
    critical_reviews = sum(1 for review in reviews if int(review.get("rating") or 0) <= 2)
    return {
        "count": count,
        "average_rating": average_rating,
        "positive_reviews": positive_reviews,
        "critical_reviews": critical_reviews,
    }


def _build_fallback_summary(stats, reviews):
    average_rating = stats["average_rating"]
    if average_rating >= 4.5:
        tone = "Riders are very happy with this trip overall."
    elif average_rating >= 3.5:
        tone = "Reviews are mostly positive overall."
    elif average_rating >= 2.5:
        tone = "Feedback is mixed for this trip."
    else:
        tone = "Reviews are mostly critical for this trip."

    recent_comments = [review["comment"] for review in reviews if review["comment"]][:2]
    if recent_comments:
        highlights = " Key themes mention " + "; ".join(recent_comments) + "."
    else:
        highlights = ""

    return (
        f"{tone} Average rating is {average_rating} from {stats['count']} review(s)."
        f"{highlights}"
    ).strip()
