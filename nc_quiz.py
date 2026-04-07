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

/* ── Global Styles ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #0b0f1a;
    color: #e0e6f0;
}

* { font-family: 'Inter', sans-serif !important; }

/* ── Hero Header ── */
.hero { text-align: center; padding: 2rem 0 1rem; }
.hero h1 {
    font-size: 3.5rem;
    font-weight: 900;
    letter-spacing: 0.05em;
    color: #e0e6f0;
    margin-bottom: 0;
}

/* ── Quiz Typography (Light Blue Theme) ── */
.q-label {
    color: #00e5ff !important;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.12em;
    margin-bottom: 0.5rem;
    text-transform: uppercase;
}

.q-text {
    font-size: 1.25rem;
    font-weight: 600;
    color: #e0e6f0;
    margin-bottom: 1.2rem;
}

/* ── Cards & Spacing ── */
.card {
    background: linear-gradient(135deg, #111827 60%, #0d1f2d);
    border: 1px solid #1e3a4f;
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
}

.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e3a4f, transparent);
    margin: 2.5rem 0;
}

/* ── Inputs ── */
div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div {
    background-color: #111827 !important;
    color: #e0e6f0 !important;
    border-color: #1e3a4f !important;
    border-radius: 8px;
}

/* ── Radio Options ── */
div[data-testid="stRadio"] div[role="radiogroup"] {
    gap: 0.8rem;
}

div[data-testid="stRadio"] label {
    background: rgba(255, 255, 255, 0.03);
    padding: 12px 16px !important;
    border-radius: 8px;
    border: 1px solid transparent;
    transition: 0.3s;
}

div[data-testid="stRadio"] label:hover {
    border-color: #00e5ff;
    background: rgba(0, 229, 255, 0.05);
}

/* ── UNIFIED WHITE FONT BUTTONS ── */
div[data-testid="stButton"] {
    display: flex;
    justify-content: center;
}

div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #0072ff, #00e5ff) !important;
    color: #ffffff !important; /* Force font color to White */
    font-weight: 700;
    font-size: 1.05rem;
    border: none !important;
    border-radius: 8px;
    padding: 0.65rem 2rem;
    box-shadow: 0 0 20px rgba(0,114,255,0.3) !important;
    width: 100% !important;
    transition: all 0.2s ease-in-out;
}

div[data-testid="stButton"] > button:hover {
    color: #ffffff !important;
    opacity: 0.9;
    box-shadow: 0 0 30px rgba(0,229,255,0.4) !important;
    transform: translateY(-1px);
}

/* ── Leaderboard Table ── */
.lb-table { width: 100%; border-collapse: collapse; }
.lb-table th { color: #9fb3c8; font-size: 0.8rem; border-bottom: 1px solid #1e3a4f; padding: 10px; }
.lb-table td { padding: 12px 10px; border-bottom: 1px solid rgba(30,58,79,0.3); }
.score-pill { background: rgba(0,229,255,0.1); padding: 4px 10px; border-radius: 6px; color: #00e5ff; }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  QUIZ QUESTIONS
# ─────────────────────────────────────────────
QUESTIONS = [
    {
        "question": "What does VUCA stand for?",
        "options": ["Volatile, Uncertain, Complex, Ambiguous", "Variable, Unified, Clear, Actionable", "Volatile, Unified, Complex, Actionable", "Variable, Uncertain, Clear, Ambiguous"],
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
        "options": ["Centralised planning with decentralised execution", "Decentralised planning with centralised execution", "Full centralised command and control", "Ad hoc decision-making at all levels"],
        "answer": "Centralised planning with decentralised execution",
    },
    {
        "question": "What is the primary purpose of an after-action review (AAR)?",
        "options": ["To assign blame for failures", "To capture lessons learned and improve future performance", "To document achievements for promotion boards", "To brief higher command on outcomes"],
        "answer": "To capture lessons learned and improve future performance",
    },
]

SQUADRONS = ["FRS", "FGS", "FSS"]

# ─────────────────────────────────────────────
#  FIREBASE INIT
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
#  SESSION STATE
# ─────────────────────────────────────────────
defaults = {"page": "join", "name": "", "squadron": "", "answers": {}, "score": None}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def calc_score(answers: dict) -> int:
    return sum(1 for i, q in enumerate(QUESTIONS) if answers.get(i) == q["answer"])

def submit_to_firestore(name, squadron, score):
    db.collection("leaderboard").add({
        "name": name, "squadron": squadron, "score": score,
        "timestamp": firestore.SERVER_TIMESTAMP, "total": len(QUESTIONS)
    })

def medal(rank: int):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}")

# ─────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────
def _render_leaderboard():
    total = len(QUESTIONS)
    try:
        docs = db.collection("leaderboard").order_by("score", direction=firestore.Query.DESCENDING).order_by("timestamp", direction=firestore.Query.ASCENDING).limit(10).stream()
        rows = [d.to_dict() for d in docs]
    except:
        st.info("Leaderboard loading...")
        return

    if not rows:
        st.write("No scores yet!")
        return

    table_rows = "".join([f"<tr><td>{medal(i+1)}</td><td>{r['name']}</td><td>{r['squadron']}</td><td><span class='score-pill'>{r['score']}/{r.get('total', total)}</span></td></tr>" for i, r in enumerate(rows)])
    st.markdown(f'<div class="card"><table class="lb-table"><thead><tr><th>#</th><th>NAME</th><th>SQN</th><th>SCORE</th></tr></thead><tbody>{table_rows}</tbody></table></div>', unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>HOW WELL DO YOU KNOW THE NCs?</h1></div>', unsafe_allow_html=True)

# ═════════════════════════════════════════════
#  PAGE: JOIN
# ═════════════════════════════════════════════
if st.session_state.page == "join":
    st.markdown("### 🏆 Live Leaderboard")
    @st.fragment(run_every=5)
    def lb_join(): _render_leaderboard()
    lb_join()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#7a8ba0;">Fill in your details to begin. One attempt only.</p>', unsafe_allow_html=True)
    
    name = st.text_input("Full Name", placeholder="e.g. ME4A Nethan Tan")
    squadron = st.selectbox("Squadron", ["— Select —"] + SQUADRONS)

    st.markdown("<br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀  JOIN & START QUIZ", use_container_width=True):
            if not name.strip() or squadron == "— Select —":
                st.error("Please fill in all details.")
            else:
                st.session_state.name, st.session_state.squadron, st.session_state.page = name.strip(), squadron, "quiz"
                st.rerun()

# ═════════════════════════════════════════════
#  PAGE: QUIZ
# ═════════════════════════════════════════════
elif st.session_state.page == "quiz":
    answered = sum(1 for i in range(len(QUESTIONS)) if st.session_state.get(f"radio_{i}"))
    total = len(QUESTIONS)
    
    st.markdown(f"{st.session_state.name} | {st.session_state.squadron}")
    st.progress(answered/total)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    for i, q in enumerate(QUESTIONS):
        st.markdown(f'<div class="q-label">Question {i+1} of {total}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="q-text">{q["question"]}</div>', unsafe_allow_html=True)
        st.radio(f"q_{i}", q["options"], index=None, key=f"radio_{i}", label_visibility="collapsed")
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🏁  SUBMIT MY ANSWERS", use_container_width=True):
            final_ans = {i: st.session_state.get(f"radio_{i}") for i in range(total)}
            if None in final_ans.values():
                st.warning("Please answer all questions before submitting.")
            else:
                score = calc_score(final_ans)
                st.session_state.score = score
                submit_to_firestore(st.session_state.name, st.session_state.squadron, score)
                st.session_state.page = "done"
                st.rerun()

# ═════════════════════════════════════════════
#  PAGE: DONE
# ═════════════════════════════════════════════
elif st.session_state.page == "done":
    st.markdown(f'<div style="text-align:center;"><h2>✅ QUIZ COMPLETE</h2><h3>Score: {st.session_state.score} / {len(QUESTIONS)}</h3></div>', unsafe_allow_html=True)
    st.markdown("---")
    _render_leaderboard()