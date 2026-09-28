# Contract Red-Flag Radar

A web app that splits a contract into clauses and rates each one Low, Medium or High risk, with a plain-English explanation. It's an aid for ordinary people, not legal advice.

**Live demo:** https://your-app-name.streamlit.app

## Tech stack
Python, Streamlit, Gemini API, SQLite, pypdf, regex

## How it works
1. Upload a PDF or .txt file, or paste the text.
2. Regex splits the text into clauses.
3. All clauses go to Gemini in one batched request with a calibrated prompt.
4. The JSON reply is parsed and shown as color-coded cards.
5. Analyses can be saved to SQLite and reopened later.

## Known limits
- The free Gemini tier allows about 20 requests a day, so the live app has a Demo mode that uses sample keyword rules instead of AI.
- Saved analyses may reset on the hosted version.
