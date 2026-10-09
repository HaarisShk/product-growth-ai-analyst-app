
import re

import streamlit as st
from databricks import sql


st.set_page_config(
    page_title="AI Product Analyst",
    page_icon="📊",
    layout="wide",
)

st.title("AI Product Analyst")
st.caption(
    "Explore product growth, retention, funnel performance, "
    "category economics, and experiments using validated Gold data."
)

# Read configuration from Streamlit Secrets.
# Never place credentials directly in this file.
try:
    db = st.secrets["databricks"]
    HOST = db["server_hostname"]
    HTTP_PATH = db["http_path"]
    TOKEN = db["access_token"]
    CATALOG = db["catalog"]
    SCHEMA = db["schema"]
except Exception:
    st.error(
        "Databricks connection settings are not configured yet. "
        "Complete the app Secrets setup before asking questions."
    )
    st.stop()

# Validate identifiers before inserting them into SQL.
for identifier in (CATALOG, SCHEMA):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        st.error("Invalid Databricks catalog or schema name in Secrets.")
        st.stop()


def table(name):
    return f"`{CATALOG}`.`{SCHEMA}`.`{name}`"


@st.cache_resource
def get_connection():
    return sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    )


def build_query():
    # Table names come from validated configuration.
    # The user's question is passed separately as a bound parameter.
    return rf"""
WITH question_input AS (
    SELECT :question AS question
),

route AS (
    SELECT
        question,
        LOWER(TRIM(
            ai_query(
                'system.ai.gpt-oss-120b',
                CONCAT(
                    'Classify the question into exactly ONE category. ',
                    'Return only the category name.',
                    '\nretention: D30 retention, acquisition channels, churn.',
                    '\nfeature_retention: feature adoption and adopter retention.',
                    '\ncategory_funnel: category checkout, payment attempts, drop-off.',
                    '\ncategory_economics: category revenue, gross profit, gross margin.',
                    '\nexperiments: A/B tests, control, treatment, experiment lift.',
                    '\ndaily_metrics: daily active users, sessions, purchases, trends.',
                    '\nproduct_funnel: overall product-view session funnel, carts, checkout, purchases.',
                    '\nQuestion: ',
                    question
                )
            )
        )) AS analytical_area
    FROM question_input
),

evidence AS (
    SELECT
        r.question,
        r.analytical_area,

        CASE
            WHEN r.analytical_area = 'retention' THEN (
                SELECT CONCAT_WS(
                    '\n',
                    COLLECT_LIST(CONCAT(
                        acquisition_channel,
                        ': ',
                        ROUND(d30_retention_pct, 2),
                        '% D30 retention; ',
                        users,
                        ' users; ',
                        retained_users,
                        ' retained.'
                    ))
                )
                FROM {table("gold_d30_retention")}
            )

            WHEN r.analytical_area = 'feature_retention' THEN (
                SELECT CONCAT_WS(
                    '\n',
                    COLLECT_LIST(CONCAT(
                        `group`,
                        ': ',
                        ROUND(d30_retention_rate, 2),
                        '% D30 retention.'
                    ))
                )
                FROM {table("gold_feature_retention")}
            )

            WHEN r.analytical_area = 'category_funnel' THEN (
                SELECT CONCAT_WS(
                    '\n',
                    COLLECT_LIST(CONCAT(
                        category,
                        ': ',
                        ROUND(
                            100.0 * (checkout_sessions - payment_sessions)
                            / NULLIF(checkout_sessions, 0),
                            2
                        ),
                        '% checkout-to-payment drop-off; ',
                        ROUND(
                            100.0 * payment_sessions
                            / NULLIF(checkout_sessions, 0),
                            2
                        ),
                        '% reached payment attempt; ',
                        checkout_sessions,
                        ' checkout sessions; ',
                        payment_sessions,
                        ' payment-attempt sessions.'
                    ))
                )
                FROM {table("gold_category_funnel")}
            )

            WHEN r.analytical_area = 'category_economics' THEN (
                SELECT CONCAT_WS(
                    '\n',
                    COLLECT_LIST(CONCAT(
                        category,
                        ': revenue ',
                        ROUND(revenue, 2),
                        '; gross profit ',
                        ROUND(gross_profit, 2),
                        '; gross margin ',
                        ROUND(
                            100.0 * gross_profit / NULLIF(revenue, 0),
                            2
                        ),
                        '%.'
                    ))
                )
                FROM {table("gold_category_economics")}
            )

            WHEN r.analytical_area = 'experiments' THEN (
                SELECT CONCAT_WS(
                    '\n',
                    COLLECT_LIST(CONCAT(
                        experiment_name,
                        ': control conversion ',
                        ROUND(control_rate, 2),
                        '%; treatment conversion ',
                        ROUND(treatment_rate, 2),
                        '%; lift ',
                        ROUND(absolute_lift_pp, 2),
                        ' percentage points; relative lift ',
                        ROUND(relative_lift_pct, 2),
                        '%; status ',
                        COALESCE(CAST(status AS STRING), 'not provided'),
                        '.'
                    ))
                )
                FROM {table("gold_experiment_results")}
            )

            WHEN r.analytical_area = 'daily_metrics' THEN (
                SELECT CONCAT_WS(
                    '\n',
                    COLLECT_LIST(CONCAT(
                        CAST(activity_date AS STRING),
                        ': active users ',
                        daily_active_users,
                        '; sessions ',
                        sessions,
                        '; purchase events ',
                        purchase_events,
                        '.'
                    ))
                )
                FROM (
                    SELECT
                        activity_date,
                        daily_active_users,
                        sessions,
                        purchase_events
                    FROM (
                        SELECT
                            activity_date,
                            daily_active_users,
                            sessions,
                            purchase_events
                        FROM {table("gold_daily_metrics")}
                        ORDER BY activity_date DESC
                        LIMIT 7
                    ) latest_days
                    ORDER BY activity_date ASC
                ) recent_days
            )

            WHEN r.analytical_area = 'product_funnel' THEN (
                SELECT CONCAT(
                    'Product funnel session-level summary:\n',
                    'Product-view sessions: ',
                    COUNT(*),
                    '\nSessions reaching add-to-cart: ',
                    COALESCE(SUM(reached_add_to_cart), 0),
                    '\nSessions reaching checkout: ',
                    COALESCE(SUM(reached_checkout), 0),
                    '\nSessions reaching purchase: ',
                    COALESCE(SUM(reached_purchase), 0),
                    '\nProduct-view-to-purchase conversion: ',
                    ROUND(
                        100.0 * SUM(reached_purchase) / NULLIF(COUNT(*), 0),
                        2
                    ),
                    '%'
                )
                FROM {table("gold_product_funnel")}
            )

            ELSE 'Unsupported analytical area. Evidence was not retrieved.'
        END AS evidence_text

    FROM route r
)

SELECT
    analytical_area,
    evidence_text,

    CASE
        WHEN evidence_text =
            'Unsupported analytical area. Evidence was not retrieved.'
        THEN evidence_text

        ELSE ai_query(
            'system.ai.gpt-oss-120b',
            CONCAT(
                'You are an AI Product Analyst. Answer using ONLY the supplied evidence.',
                '\nRules:',
                '\n- Never invent, estimate, or alter counts or metrics.',
                '\n- Copy supplied counts and percentages exactly.',
                '\n- Do not calculate new counts mentally.',
                '\n- Do not claim causation from observational data.',
                '\n- Do not claim LTV, ROI, or acquisition cost unless supplied.',
                '\n- Payment attempts are not confirmed successful payments.',
                '\n- Purchase events are not payment attempts.',
                '\n- State when evidence is insufficient.',
                '\n- Separate observed facts from interpretation.',
                '\n- Do not infer recurring weekly patterns from one seven-day window.',
                '\n- State exact dates and values when comparing changes.',
                '\n- Do not imply statistical significance without test results.',
                '\n- Use observational language rather than causal language.',
                '\n- Feature adoption and retention comparisons are observational unless randomized.',
                '\n- Do not recommend changes solely from descriptive comparisons.',
                '\n- Distinguish observed experiment lift from statistical significance.',
                '\n- Never invent or change a count from the evidence.',
                '\n- Do not infer individual behavior from aggregate metrics.',
                '\n- D30 retention is not a customer-level churn prediction.',
                '\n- Do not predict future churn unless model predictions are supplied.',
                '\n- Do not invent customer names or answer beyond the evidence.',
                '\n- Keep the answer concise.',
                '\n\nQuestion: ',
                question,
                '\n\nAnalytical area: ',
                analytical_area,
                '\n\nEvidence:\n',
                evidence_text
            )
        )
    END AS ai_answer

FROM evidence
"""

QUERY = build_query()


def ask_analyst(question):
    with get_connection().cursor() as cursor:
        cursor.execute(
            QUERY,
            parameters={"question": question},
        )
        row = cursor.fetchone()

        if row is None:
            raise RuntimeError("The query returned no results.")

        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))


with st.sidebar:
    st.subheader("Ask about")
    st.markdown(
        "- Retention and acquisition\n"
        "- Feature adoption\n"
        "- Category funnel drop-off\n"
        "- Revenue and gross profit\n"
        "- A/B experiments\n"
        "- Daily activity\n"
        "- Product funnel"
    )
    st.caption(
        "Answers are grounded in available Gold-table evidence. "
        "They may still require human verification."
    )

with st.form("analyst_question"):
    question = st.text_area(
        "What would you like to know?",
        placeholder=(
            "Example: Which category has the biggest "
            "checkout-to-payment drop-off?"
        ),
        height=100,
        max_chars=1000,
    )
    submitted = st.form_submit_button(
        "Ask AI Analyst",
        type="primary",
    )

if submitted:
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            with st.spinner("Retrieving evidence and generating an answer..."):
                result = ask_analyst(question.strip())

            st.subheader("Answer")
            st.markdown(result["ai_answer"] or "No answer was returned.")

            with st.expander("View analytical area and evidence"):
                st.write("**Route:**", result["analytical_area"])
                st.text(result["evidence_text"])

        except Exception:
            st.error(
                "The query failed. Check the Databricks Secrets, "
                "SQL Warehouse availability, table permissions, "
                "and AI function access."
            )
            st.info(
                "If the problem persists, inspect the Streamlit app logs "
                "for the detailed error. Do not share access tokens."
            )
