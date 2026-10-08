# Raremotion Support AI

AI-powered customer support grounded in business knowledge supplied by the user.

## Run locally

Install requirements, configure `OPENAI_API_KEY` in a local `.env` file, and run `streamlit run app.py`.

## Deployment

Deploy `app.py` from the `main` branch using Python 3.14 on Streamlit Community Cloud.
Set `OPENAI_API_KEY` in the hosting dashboard's Secrets settings as a root-level TOML string. Never commit the key, `.env`, or `.streamlit/secrets.toml`.

Business knowledge and conversations belong to the browser session; they are not saved to a shared database. Reloading or disconnecting may clear them. Submitted business knowledge and questions are sent to OpenAI to generate answers. API response storage is disabled.

## Accounts and free answers

Visitors see Create Account first, with Log In for existing accounts. Email confirmation is required before the workspace opens. Analytics accounts can also log in; Support AI tracks its own two successful answers separately. Failed AI calls release their reservation, and the database prevents a third answer.

Streamlit Secrets must contain `SUPABASE_URL`, `SUPABASE_KEY` (publishable key), and `SUPPORT_AI_GATE_SECRET`, alongside `OPENAI_API_KEY`. Never commit credentials. The deployed Supabase project must have `schema.sql` installed and a matching SHA-256 gate-secret hash in the private config table. Allow `https://raremotion-support-ai.streamlit.app/` as an authentication redirect. Supabase email delivery limits apply; production public signup requires a properly configured email provider.

Run tests with `python -m unittest discover -s tests -v`. `tests/quota.sql` runs allowance and isolation assertions inside a transaction and rolls back all fixtures.
