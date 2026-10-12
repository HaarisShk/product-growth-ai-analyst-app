# AI Product Analyst

**Live demo:** [Launch AI Product Analyst](https://appuct-growth-ai-analyst-app-en72jecgo9kfsvtakmmhnp.streamlit.app/)

A Streamlit application for asking natural-language questions about product-growth metrics. The app routes supported questions to existing Databricks Gold-table evidence and uses an AI model to explain retrieved results and product analytics terminology.

## What it supports

- Product funnel and conversion questions
- D30 retention and acquisition-channel comparisons
- Feature adoption and retention comparisons
- Category funnel and economics
- Experiment-result interpretation
- Daily metrics and product analytics definitions/formulas

## Architecture

Streamlit UI → intent routing → read-only Databricks SQL queries against existing Gold tables → evidence-backed response, with an AI layer for explanations. 

## Run locally

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Configure a `.streamlit/secrets.toml` file locally with the required Databricks settings.
4. Run `streamlit run app.py`.

The exact configuration keys must match the current `app.py` and the deployed Streamlit configuration. Never commit `secrets.toml`, access tokens, passwords, or credential-bearing connection strings. Use Streamlit Community Cloud Secrets for deployment and a least-privilege, read-only Databricks identity where supported.

## Limitations

- The project data is synthetic/generated and does not describe a real business.
- Observational comparisons do not prove causation.
- Payment attempts are not the same as successful payments.
- Experiment conclusions depend on the test design and statistical evidence.
- The app depends on the configured Databricks warehouse, Gold tables, and AI function; it is not a standalone recreation of the data pipeline.

See the [main analytics repository](https://github.com/HaarisShk/product-growth-ai-analyst) for project methodology, data definitions, notebook workflow, and findings.
