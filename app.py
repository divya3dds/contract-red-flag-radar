import streamlit as st
import re
import os
import json
import time
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
import database

st.set_page_config(page_title="Contract Red-Flag Radar", page_icon="🚩", layout="centered")

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
database.init_db()

# ---------- Header ----------
st.title("🚩 Contract Red-Flag Radar")
st.caption("Paste or upload a contract and see which clauses may be risky before you sign. This is an AI-generated aid, not legal advice.")

# ---------- Sidebar ----------
demo_mode = st.sidebar.checkbox("Demo mode (no API, sample results)")
if demo_mode:
    st.info("Demo mode is ON: results are sample keyword-based output, not real AI analysis.")

st.sidebar.markdown("---")
st.sidebar.subheader("Past analyses")
for row in database.list_analyses():
    analysis_id, saved_title, created_at = row
    if st.sidebar.button(f"{saved_title} ({created_at})", key=f"load_{analysis_id}"):
        st.session_state["current"] = database.load_analysis(analysis_id)

# ---------- Input ----------
uploaded_file = st.file_uploader("Upload a contract (PDF or .txt)", type=["pdf", "txt"])
contract_text = ""
title = ""

if uploaded_file is not None:
    title = uploaded_file.name
    if uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                contract_text += extracted + "\n"
    else:
        contract_text = uploaded_file.read().decode("utf-8")
    with st.expander("Extracted text preview"):
        st.text(contract_text)
else:
    contract_text = st.text_area("Or paste contract text here:", height=250)
    title = contract_text.strip()[:30] + "..." if contract_text.strip() else ""


# ---------- Analysis functions ----------
def analyze_demo(clauses):
    results = []
    for i, c in enumerate(clauses, start=1):
        text = c.lower()
        if "non-refundable" in text or "without prior notice" in text or "regardless of cause" in text:
            risk, why = "High", "Demo result: contains wording that is commonly one-sided or unfair."
        elif "automatically renew" in text or "penalty" in text:
            risk, why = "Medium", "Demo result: common clause, but worth double-checking the terms."
        else:
            risk, why = "Low", "Demo result: no obviously risky wording found."
        results.append({"clause_number": i, "risk": risk, "explanation": why})
    return results


def analyze_all_clauses(clauses, max_retries=3):
    numbered_clauses = "\n\n".join(f"Clause {i + 1}: {c}" for i, c in enumerate(clauses))

    prompt = f"""You are a contract-review assistant helping an ordinary person (not a lawyer) understand a contract.

Below are numbered clauses from a contract. For EACH clause, judge how risky or unusual it is for the person signing it (not the party who wrote it), using these calibration guidelines:
- Low risk: standard, fair, commonly seen in everyday contracts (e.g. normal notice periods, standard payment terms)
- Medium risk: slightly one-sided or worth double-checking, but not alarming (e.g. auto-renewal clauses, moderate penalty fees)
- High risk: seriously unfair, unusual, or could cause major financial/legal harm (e.g. non-refundable deposits, waiving legal rights, unlimited liability)

Clauses:
{numbered_clauses}

Respond ONLY with a valid JSON array, no markdown, no extra text, in this exact format:
[
  {{"clause_number": 1, "risk": "Low", "explanation": "..."}},
  {{"clause_number": 2, "risk": "Medium", "explanation": "..."}}
]

Return exactly {len(clauses)} objects, one per clause, in order.
"""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            text = response.text.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                raise Exception("Gemini API quota exceeded. Try again after the daily reset, or tick Demo mode in the sidebar.")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise e


# ---------- Analyze button ----------
if contract_text and st.button("Analyze contract", type="primary"):
    clauses = re.split(r"\n\s*\n|\n(?=\d+\.)", contract_text)
    clauses = [c.strip() for c in clauses if c.strip()]
    try:
        if demo_mode:
            results = analyze_demo(clauses)
        else:
            with st.spinner("Analyzing all clauses..."):
                results = analyze_all_clauses(clauses)
        st.session_state["current"] = {
            "title": title + (" [demo]" if demo_mode else ""),
            "clauses": clauses,
            "results": results,
            "saved": False,
        }
    except Exception as e:
        st.error(f"Analysis failed: {e}")

# ---------- Results ----------
current = st.session_state.get("current")
if current:
    st.divider()
    st.subheader(current["title"])

    results = current["results"]
    clauses = current["clauses"]

    counts = {"High": 0, "Medium": 0, "Low": 0}
    for r in results:
        if r.get("risk") in counts:
            counts[r["risk"]] += 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clauses", len(results))
    c2.metric("🔴 High", counts["High"])
    c3.metric("🟠 Medium", counts["Medium"])
    c4.metric("🟢 Low", counts["Low"])

    if not current["saved"]:
        if st.button("Save this analysis"):
            database.save_analysis(current["title"], current["clauses"], current["results"])
            current["saved"] = True
            st.success("Saved! It now appears under Past analyses in the sidebar.")

    risk_filter = st.radio("Show:", ["All", "High", "Medium", "Low"], horizontal=True)

    order = {"High": 0, "Medium": 1, "Low": 2}
    sorted_results = sorted(results, key=lambda r: order.get(r.get("risk"), 3))

    for r in sorted_results:
        risk = r.get("risk", "Unknown")
        if risk_filter != "All" and risk != risk_filter:
            continue

        idx = r.get("clause_number", "?")
        explanation = r.get("explanation", "")
        clause_text = clauses[idx - 1] if isinstance(idx, int) and 0 < idx <= len(clauses) else ""
        color = {"Low": "green", "Medium": "orange", "High": "red"}.get(risk, "gray")

        with st.container(border=True):
            left, right = st.columns([4, 1])
            left.markdown(f"**Clause {idx}**")
            right.markdown(f":{color}-background[{risk} risk]")
            st.write(clause_text)
            st.markdown(f"**Why:** {explanation}")