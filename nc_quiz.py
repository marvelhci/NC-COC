import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import time

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="How Well Do You Know the NCs?",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS  — military/gamified dark theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

/* ── global: font + page bg only — no wildcard background ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #0b0f1a;
    color: #e0e6f0;
}

/* keep font consistent without nuking button/input backgrounds */
* {
    font-family: 'Inter', sans-serif !important;
}

/* ── hero header ── */
.hero {
    text-align: center;
    padding: 2rem 0 1rem;
}
.hero h1 {
    font-size: 4rem;
    font-weight: 900;
    letter-spacing: 0.05em;
    color: #e0e6f0;
    text-shadow: none;
    margin-bottom: 0;
}

/* ── cards ── */
.card {
    background: linear-gradient(135deg, #111827 60%, #0d1f2d);
    border: 1px solid #1e3a4f;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 30px rgba(0,229,255,0.05);
}

/* ── join description ── */
.join-desc {
    font-weight: 300;
    font-style: italic;
    color: #7a8ba0;
    font-size: 0.95rem;
}

/* ── input labels ── */
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label {
    font-size: 1.1rem;
    font-weight: 400;
}

/* ── input fields ── */
div[data-testid="stTextInput"] input {
    background-color: #111827 !important;
    color: #e0e6f0 !important;
    border-color: #1e3a4f !important;
    border-radius: 8px;
}

div[data-testid="stSelectbox"] div {
    background-color: #111827 !important;
    color: #e0e6f0 !important;
    border-color: #1e3a4f !important;
    border-radius: 8px;
}

/* ── button wrapper: transparent bg, centered ── */
div[data-testid="stButton"],
div.stButton {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    display: flex;
    justify-content: center;
}

/* ── button itself ── */
div[data-testid="stButton"] > button,
div.stButton > button {
    background: linear-gradient(135deg, #0072ff, #00e5ff) !important;
    color: #0b0f1a !important;
    font-weight: 700;
    font-size: 1.05rem;
    border: none !important;
    border-radius: 8px;
    padding: 0.65rem 2rem;
    width: auto;
    box-shadow: 0 0 20px rgba(0,114,255,0.3) !important;
    outline: none !important;
}

div[data-testid="stButton"] > button:hover,
div.stButton > button:hover {
    opacity: 0.88;
}

/* ── radio options ── */
div[data-testid="stRadio"] label {
    color: #b0c4d8 !important;
    font-size: 1rem;
}

div[data-testid="stRadio"] label:hover {
    color: #00e5ff !important;
}

/* ── progress bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #00e5ff, #0072ff);
}

/* ── divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e3a4f, transparent);
    margin: 1.5rem 0;
}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  QUIZ QUESTIONS  — edit freely
# ─────────────────────────────────────────────
QUESTIONS = [
    {
        "question": "What does VUCA stand for?",
        "options": [
            "Volatile, Uncertain, Complex, Ambiguous",
            "Variable, Unified, Clear, Actionable",
            "Volatile, Unified, Complex, Actionable",
            "Variable, Uncertain, Clear, Ambiguous",
        ],
        "answer": "Volatile, Uncertain, Complex, Ambiguous",
    },
    {
        "question": "Which leadership style involves the leader making decisions without team input?",
        "options": ["Democratic", "Laissez-faire", "Autocratic", "Transformational"],
        "answer": "Autocratic",
    },
    {
        "question": "In the OODA loop, what does the second 'O' stand for?",
        "options": ["Objective", "Orient", "Operate", "Organise"],
        "answer": "Orient",
    },
    {
        "question": "Which of the following best describes 'mission command'?",
        "options": [
            "Centralised planning with decentralised execution",
            "Decentralised planning with centralised execution",
            "Full centralised command and control",
            "Ad hoc decision-making at all levels",
        ],
        "answer": "Centralised planning with decentralised execution",
    },
    {
        "question": "What is the primary purpose of an after-action review (AAR)?",
        "options": [
            "To assign blame for failures",
            "To capture lessons learned and improve future performance",
            "To document achievements for promotion boards",
            "To brief higher command on outcomes",
        ],
        "answer": "To capture lessons learned and improve future performance",
    },
    # ── Add more questions below ──────────────────────────────────────────
    # {
    #     "question": "Your question here?",
    #     "options": ["A", "B", "C", "D"],
    #     "answer": "Correct option exactly as written above",
    # },
]

SQUADRONS = ["FRS", "FGS", "FSS"]

# ─────────────────────────────────────────────
#  FIREBASE INIT  (singleton via cache_resource)
# ─────────────────────────────────────────────
@st.cache_resource
def get_firestore_client():
    if not firebase_admin._apps:
        key_dict = {
            "type":                        st.secrets["firebase"]["type"],
            "project_id":                  st.secrets["firebase"]["project_id"],
            "private_key_id":              st.secrets["firebase"]["private_key_id"],
            "private_key":                 st.secrets["firebase"]["private_key"],
            "client_email":                st.secrets["firebase"]["client_email"],
            "client_id":                   st.secrets["firebase"]["client_id"],
            "auth_uri":                    st.secrets["firebase"]["auth_uri"],
            "token_uri":                   st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url":        st.secrets["firebase"]["client_x509_cert_url"],
        }
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

# ─────────────────────────────────────────────
#  SESSION STATE DEFAULTS
# ─────────────────────────────────────────────
defaults = {
    "page": "join",
    "name": "",
    "squadron": "",
    "answers": {},
    "score": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def calc_score(answers: dict) -> int:
    return sum(
        1 for i, q in enumerate(QUESTIONS)
        if answers.get(i) == q["answer"]
    )

def submit_to_firestore(name: str, squadron: str, score: int):
    db.collection("leaderboard").add({
        "name":      name,
        "squadron":  squadron,
        "score":     score,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "total":     len(QUESTIONS),
    })

def medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}")

# ─────────────────────────────────────────────
#  HERO HEADER (shown on every page)
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>HOW WELL DO YOU KNOW THE NCs?</h1>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LIVE LEADERBOARD HELPER  (plain function, called inside fragments per page)
# ─────────────────────────────────────────────
def _render_leaderboard():
    total = len(QUESTIONS)
    try:
        docs = (
            db.collection("leaderboard")
              .order_by("score", direction=firestore.Query.DESCENDING)
              .order_by("timestamp", direction=firestore.Query.ASCENDING)
              .limit(10)
              .stream()
        )
        rows = [d.to_dict() for d in docs]
    except Exception:
        st.markdown("<div style='color:#ffcc00;'>⏳ Leaderboard loading… (~1 min)</div>", unsafe_allow_html=True)
        return

    if not rows:
        st.markdown("<div style='color:#9aa7b5;'>No scores yet — be the first!</div>", unsafe_allow_html=True)
        return

    table_rows = ""
    for rank, row in enumerate(rows, start=1):
        name_val  = row.get("name", "—")
        sqn_val   = row.get("squadron", "—")
        score_val = row.get("score", 0)
        ttl_val   = row.get("total", total)
        badge     = medal(rank)
        table_rows += f"""
        <tr>
          <td><span class="rank-badge">{badge}</span></td>
          <td>{name_val}</td>
          <td>{sqn_val}</td>
          <td><span class="score-pill">{score_val}/{ttl_val}</span></td>
        </tr>"""

    st.markdown(f"""
    <div class="card">
      <table class="lb-table">
        <thead>
          <tr>
            <th>#</th><th>NAME</th><th>SQUADRON</th><th>SCORE</th>
          </tr>
        </thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

# ═════════════════════════════════════════════
#  PAGE: JOIN
# ═════════════════════════════════════════════
if st.session_state.page == "join":
    st.markdown("### 🏆 Live Leaderboard")

    @st.fragment(run_every=5)
    def leaderboard_join():
        _render_leaderboard()

    leaderboard_join()

    st.markdown("---")
    st.markdown('<div class="join-desc">Fill in your details to begin. You have <b>one attempt</b> — make it count.</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    name = st.text_input("Full Name", placeholder="e.g. ME4A Nethan Tan", max_chars=60)
    squadron = st.selectbox("Squadron", ["— Select —"] + SQUADRONS)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀  JOIN & START QUIZ"):
        if not name.strip():
            st.markdown("<div style='color:#ff6b6b;'>Please enter your name.</div>", unsafe_allow_html=True)
        elif squadron == "— Select —":
            st.markdown("<div style='color:#ff6b6b;'>Please select your squadron.</div>", unsafe_allow_html=True)
        else:
            st.session_state.name = name.strip()
            st.session_state.squadron = squadron
            st.session_state.page = "quiz"
            st.rerun()

# ═════════════════════════════════════════════
#  PAGE: QUIZ
# ═════════════════════════════════════════════
elif st.session_state.page == "quiz":
    answered = len(st.session_state.answers)
    total    = len(QUESTIONS)
    progress = answered / total

    st.markdown(f"**{st.session_state.name}** · {st.session_state.squadron}")
    st.progress(progress, text=f"{answered}/{total} answered")
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("quiz_form"):
        for i, q in enumerate(QUESTIONS):
            st.markdown(f'<div class="q-label">QUESTION {i+1} OF {total}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="q-text">{q["question"]}</div>', unsafe_allow_html=True)
            choice = st.radio(
                label=f"q{i}",
                options=q["options"],
                index=None,
                label_visibility="collapsed",
                key=f"radio_{i}",
            )
            if choice:
                st.session_state.answers[i] = choice
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        submitted = st.form_submit_button("🏁  SUBMIT MY ANSWERS", use_container_width=True)

    if submitted:
        final_answers = {
            i: st.session_state.get(f"radio_{i}")
            for i in range(total)
            if st.session_state.get(f"radio_{i}") is not None
        }
        unanswered = total - len(final_answers)
        if unanswered > 0:
            st.markdown(f"<div style='color:#ffcc00;'>⚠️ You have {unanswered} unanswered question(s).</div>", unsafe_allow_html=True)
        else:
            score = calc_score(final_answers)
            st.session_state.score = score
            with st.spinner("Uploading your score…"):
                submit_to_firestore(
                    st.session_state.name,
                    st.session_state.squadron,
                    score,
                )
            st.session_state.page = "done"
            st.rerun()

# ═════════════════════════════════════════════
#  PAGE: DONE  (success + live leaderboard)
# ═════════════════════════════════════════════
elif st.session_state.page == "done":
    score = st.session_state.score
    total = len(QUESTIONS)
    pct   = round(score / total * 100)

    st.markdown(f"""
    <div class="success-banner">
      <h2>✅ SUBMISSION COMPLETE</h2>
      <p>Well done, <strong>{st.session_state.name}</strong> ({st.session_state.squadron})</p>
      <p style="font-size:1.8rem;font-weight:700;color:#e0e6f0;margin-top:0.5rem;font-family:'Inter',sans-serif;">
        {score} / {total} &nbsp;·&nbsp; {pct}%
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🏆 Live Leaderboard")

    @st.fragment(run_every=5)
    def leaderboard_done():
        _render_leaderboard()

    leaderboard_done()