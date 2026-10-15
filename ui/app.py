"""Streamlit interface for the movie recommendation API."""

import os
from html import escape

import httpx
import streamlit as st


API_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
# Apply a cinema-inspired black, red, and white palette.
_original_markdown = st.markdown

def themed_markdown(body, *args, **kwargs):
    """Apply the interface palette to custom HTML and CSS."""
    if isinstance(body, str) and kwargs.get("unsafe_allow_html"):
        replacements = {
            "#0b0d14": "#0b0b0b",
            "#eef0f8": "#f5f5f1",
            "#a78bfa": "#e50914",
            "#b8a0ff": "#ff424b",
            "#ad91ff": "#e50914",
            "#9ca3b8": "#b3b3b3",
            "#171422": "#1c1011",
            "#302640": "#502025",
            "#cab8ff": "#ffb3b7",
            "#191c2b": "#202020",
            "#12151f": "#141414",
            "#292d40": "#333333",
            "#b6bdd1": "#cccccc",
            "#232739": "#303030",
            "#f1f3fb": "#ffffff",
            "#a4acc1": "#b3b3b3",
            "#949db4": "#aaaaaa",
            "#252938": "#303030",
            "#747e97": "#808080",
            "#8860e8": "#e50914",
            "#9b75f5": "#f6121d",
        }
        for original, replacement in replacements.items():
            body = body.replace(original, replacement)
    return _original_markdown(body, *args, **kwargs)

st.markdown = themed_markdown

st.set_page_config(
    page_title="CineGraph | Movie Discovery",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background: #0b0d14;
        color: #eef0f8;
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .brand {
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 3rem;
    }

    .brand span { color: #a78bfa; }

    .eyebrow {
        color: #b8a0ff;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.9rem;
    }

    .hero-title {
        font-size: clamp(2.8rem, 6vw, 4.8rem);
        font-weight: 800;
        line-height: 1.05;
        letter-spacing: -0.065em;
        margin: 0;
    }

    .hero-title span { color: #ad91ff; }

    .hero-description {
        color: #9ca3b8;
        font-size: 1rem;
        line-height: 1.8;
        max-width: 620px;
        margin-top: 1.3rem;
        margin-bottom: 2rem;
    }

    .hero-note {
        display: inline-block;
        background: #171422;
        border: 1px solid #302640;
        border-radius: 100px;
        padding: 0.45rem 0.9rem;
        color: #cab8ff;
        font-size: 0.76rem;
        margin-bottom: 2.7rem;
    }

    .movie-card {
        background: linear-gradient(135deg, #191c2b, #12151f);
        border: 1px solid #292d40;
        border-radius: 18px;
        padding: 1.35rem;
        min-height: 185px;
        margin-bottom: 1rem;
    }

    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.3rem;
    }

    .movie-number {
        color: #a78bfa;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.06em;
    }

    .movie-badge {
        color: #b6bdd1;
        background: #232739;
        padding: 0.25rem 0.6rem;
        border-radius: 7px;
        font-size: 0.68rem;
    }

    .movie-title {
        color: #f1f3fb;
        font-weight: 700;
        font-size: 1.08rem;
        line-height: 1.5;
        margin-bottom: 0.8rem;
    }

    .movie-detail {
        color: #a4acc1;
        font-size: 0.8rem;
        line-height: 1.7;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        margin-top: 1.5rem;
        margin-bottom: 0.4rem;
    }

    .section-description {
        color: #949db4;
        font-size: 0.88rem;
        margin-bottom: 1.5rem;
    }

    .footer {
        border-top: 1px solid #252938;
        color: #747e97;
        font-size: 0.75rem;
        margin-top: 3rem;
        padding-top: 1.2rem;
    }

    .stButton > button,
    .stFormSubmitButton > button {
        border-radius: 10px;
        font-weight: 600;
    }

    button[kind="primary"] {
        background: #8860e8;
        border: 1px solid #8860e8;
        color: white;
    }

    button[kind="primary"]:hover {
        background: #9b75f5;
        border-color: #9b75f5;
        color: white;
    }

    div[data-baseweb="tab-list"] {
        gap: 1.3rem;
        border-bottom: 1px solid #292d40;
    }

    button[data-baseweb="tab"] {
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(method, path, **kwargs):
    """Call the backend and display readable errors."""
    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.request(
                method, f"{API_URL}{path}", **kwargs
            )

        if response.is_error:
            try:
                detail = response.json().get(
                    "detail", "The request could not be completed."
                )
            except ValueError:
                detail = "The request could not be completed."

            if response.status_code == 404:
                st.warning(
                    "That user or movie was not found. Try another ID."
                )
            else:
                st.error(
                    detail if isinstance(detail, str)
                    else "Please check your input and try again."
                )
            return None

        return response.json()

    except httpx.RequestError:
        st.error(
            "We couldn’t reach the recommendation service. "
            "Make sure FastAPI is running, then try again."
        )
        return None


def section(title, description):
    """Display a consistent section heading."""
    st.markdown(
        f'<div class="section-title">{escape(title)}</div>'
        f'<div class="section-description">{escape(description)}</div>',
        unsafe_allow_html=True,
    )


def movie_cards(movies, mode):
    """Display API results as a responsive grid."""
    if not movies:
        st.info("No matching movies were found for this selection.")
        return

    columns = st.columns(3)

    for index, movie in enumerate(movies):
        if mode == "recommendations":
            badge = "FOR YOU"
            detail = (
                f"{movie['supportingUsers']} supporting viewers"
                f" · Average rating {movie['averageRating']:.2f}/5"
            )
        elif mode == "similar":
            badge = "SIMILAR AUDIENCE"
            detail = (
                f"Audience similarity {movie['similarity']:.1%}"
                f" · {movie['commonLikers']} shared fans"
            )
        elif mode == "discover":
            badge = "COMMUNITY PICK"
            detail = (
                f"{movie['likedInCommunity']} of your liked films "
                f"in this community"
            )
        else:
            badge = "NETWORK RANK"
            detail = f"PageRank score {movie['pageRank']:.3f}"

        with columns[index % 3]:
            st.markdown(
                f"""
                <div class="movie-card">
                    <div class="card-top">
                        <span class="movie-number">#{index + 1:02d}</span>
                        <span class="movie-badge">{escape(badge)}</span>
                    </div>
                    <div class="movie-title">
                        {escape(movie["title"])}
                    </div>
                    <div class="movie-detail">{escape(detail)}</div>
                    <div class="movie-detail">
                        Movie ID · {int(movie["movieId"])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


st.markdown(
    '<div class="brand">cine<span>graph</span> /</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="eyebrow">CONNECTED TASTES. BETTER DISCOVERIES.</div>
    <h1 class="hero-title">Your next great film.<br>
    <span>Already connected to you.</span></h1>
    <p class="hero-description">
    Discover films through people who share your taste.
    Explore similar audiences, uncover movie communities,
    and see the connections behind every recommendation.
    </p>
    <div class="hero-note">
    MovieLens collection · Graph-powered discovery
    </div>
    """,
    unsafe_allow_html=True,
)

for_you, similar, discover, network, assistant = st.tabs(
    ["For you", "Similar films", "Discover", "Network highlights", "Ask CineGraph"]
)

with for_you:
    section(
        "A new watchlist, built around your taste",
        "Choose a MovieLens user to explore recommendations "
        "from viewers with shared favorites.",
    )

    with st.form("recommendation_form"):
        first, second = st.columns([2, 1])
        user_id = first.number_input(
            "User ID", min_value=1, value=1, step=1
        )
        limit = second.selectbox(
            "Number of films", [6, 9, 12], index=0
        )
        submitted = st.form_submit_button(
            "Find my next film", type="primary"
        )

    if submitted:
        with st.spinner("Following your movie connections…"):
            results = api_request(
                "GET",
                f"/api/users/{user_id}/recommendations",
                params={"limit": limit},
            )
        if results is not None:
            st.session_state["recommendations"] = {
                "user_id": user_id,
                "movies": results,
            }

    saved = st.session_state.get("recommendations")
    if saved is not None:
        st.caption(f"Recommendations for user {saved['user_id']}")
        movie_cards(saved["movies"], "recommendations")

        if saved["movies"]:
            with st.expander("Why were these films recommended?"):
                chosen = st.selectbox(
                    "Explore the evidence",
                    options=saved["movies"],
                    format_func=lambda movie: movie["title"],
                )

                if st.button("Show graph evidence"):
                    evidence = api_request(
                        "GET",
                        f"/api/users/{saved['user_id']}"
                        f"/recommendations/{chosen['movieId']}/why",
                    )
                    if evidence:
                        st.success(
                            f"{len(evidence)} viewers with shared "
                            "favorites also liked this film."
                        )
                        for item in evidence[:5]:
                            st.markdown(
                                f"**Viewer {item['supportingUserId']}** "
                                f"· {item['sharedLikes']} shared favorites "
                                f"· Rated this film "
                                f"**{item['recommendedMovieRating']}/5**"
                            )
                            st.caption(
                                "Shared favorites: "
                                + ", ".join(item["sharedMovies"])
                            )
                    elif evidence == []:
                        st.info("No supporting evidence was found.")

with similar:
    section(
        "Loved a film? Follow its audience.",
        "Find films liked by overlapping audiences. "
        "Similarity measures shared viewers, rather than plot or genre.",
    )
    with st.form("similar_form"):
        first, second = st.columns([2, 1])
        movie_id = first.number_input(
            "Movie ID · try 1 for Toy Story",
            min_value=1,
            value=1,
            step=1,
        )
        similar_limit = second.selectbox(
            "Number of films", [6, 9, 10]
        )
        submitted = st.form_submit_button(
            "Explore similar films", type="primary"
        )

    if submitted:
        with st.spinner("Finding connected audiences…"):
            results = api_request(
                "GET",
                f"/api/movies/{movie_id}/similar",
                params={"limit": similar_limit},
            )
        if results is not None:
            movie_cards(results, "similar")

with discover:
    section(
        "Find your corner of cinema",
        "Explore unseen films from communities containing "
        "your liked movies, ordered by community preference "
        "and network centrality.",
    )
    with st.form("discovery_form"):
        discovery_user = st.number_input(
            "User ID", min_value=1, value=1, step=1,
            key="discovery_user",
        )
        submitted = st.form_submit_button(
            "Discover community picks", type="primary"
        )

    if submitted:
        with st.spinner("Exploring your movie communities…"):
            results = api_request(
                "GET",
                f"/api/users/{discovery_user}/discover",
                params={"limit": 9},
            )
        if results is not None:
            movie_cards(results, "discover")

with network:
    section(
        "Films at the heart of the network",
        "Ranked by PageRank on the movie similarity graph. "
        "These are historical network highlights, not current "
        "box-office trends or average-rating rankings.",
    )
    if st.button("Explore network highlights", type="primary"):
        with st.spinner("Loading network highlights…"):
            results = api_request(
                "GET", "/api/movies/trending",
                params={"limit": 9},
            )
        if results is not None:
            movie_cards(results, "network")

with assistant:
    section(
        "Ask for your next discovery",
        "Use a user ID for personalized recommendations "
        "or a movie ID for similar films.",
    )
    st.caption(
        'Try: “Recommend 5 movies for user 1” or '
        '“Find 3 movies similar to movie 1”.'
    )

    with st.form("assistant_form"):
        question = st.text_input(
            "Your question",
            placeholder="Recommend 5 movies for user 1",
            max_chars=500,
        )
        submitted = st.form_submit_button(
            "Ask CineGraph", type="primary"
        )

    if submitted:
        if len(question.strip()) < 3:
            st.warning("Enter a question first.")
        else:
            with st.spinner("Understanding your request…"):
                answer = api_request(
                    "POST", "/api/ask",
                    json={"question": question.strip()},
                )

            if answer is not None:
                mode = (
                    "recommendations"
                    if answer["queryName"] == "recommendations"
                    else "similar"
                )
                st.caption(
                    "Results retrieved from the movie graph "
                    "using an approved query."
                )
                movie_cards(answer["results"], mode)

                with st.expander("View query transparency"):
                    st.json(answer["parameters"])
                    st.code(answer["cypher"], language="cypher")

st.markdown(
    """
    <div class="footer">
    CineGraph · MovieLens data · Recommendations with graph evidence
    </div>
    """,
    unsafe_allow_html=True,
)
