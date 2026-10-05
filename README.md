# Raremotion Support AI

AI-powered customer support grounded in business knowledge supplied by the user.

## Run locally

Install requirements, configure `OPENAI_API_KEY` in a local `.env` file, and run `streamlit run app.py`.

## Deployment

Deploy `app.py` from the `main` branch using Python 3.13 on Streamlit Community Cloud.
Set `OPENAI_API_KEY` in the hosting dashboard's Secrets settings as a root-level TOML string. Never commit the key, `.env`, or `.streamlit/secrets.toml`.

Business knowledge and conversations belong to the browser session; they are not saved to a shared database. Reloading or disconnecting may clear them. Submitted business knowledge and questions are sent to OpenAI to generate answers. API response storage is disabled.
