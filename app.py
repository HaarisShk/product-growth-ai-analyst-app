        "Which acquisition channel has the lowest D30 retention?",
        "Which category generates the most gross profit?",
    ],
    "⚑  Funnel": [
        "Which category has the biggest checkout-to-payment drop-off?",
        "What is the overall product funnel conversion rate?",
        "Which category has the lowest payment-attempt rate?",
    ],
    "↗  Retention": [
        "Which acquisition channel has the lowest D30 retention?",
        "Is feature adoption associated with higher D30 retention?",
        "Compare D30 retention across acquisition channels.",
    ],
    "⊙  Revenue": [
        "Which category generates the most gross profit?",
        "Which category has the highest gross margin?",
        "Compare category revenue and gross profit.",
    ],
    "♧  Experiments": [
        "Which experiment showed the strongest conversion lift?",
        "Which experiments have statistically significant results?",
        "Summarize the experiment results.",
    ],
}

with st.sidebar:
    st.markdown('<div class="brand-row"><span class="brand-mark">A</span><span>Insight</span></div>', unsafe_allow_html=True)
    selected_nav = st.radio("Navigation", list(NAV_QUESTIONS), label_visibility="collapsed", key="selected_nav")
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.caption("Grounded in Gold-table data")
    st.markdown("<div class='small-note'>Answers use validated evidence. Observational patterns do not establish causation.</div>", unsafe_allow_html=True)

# ------------------------------ Main page -----------------------------------
st.markdown('<div class="eyebrow">PRODUCT GROWTH INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">What do you want to know?</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Ask a business question. Get a clear finding and the data behind it.</div>', unsafe_allow_html=True)

suggestions = NAV_QUESTIONS[selected_nav]
for col, suggestion in zip(st.columns(len(suggestions)), suggestions):
    col.button(suggestion, key=f"suggestion_{selected_nav}_{suggestion}",
               on_click=fill_question, args=(suggestion,), **STRETCH)

with st.form("analyst_question_form"):
    input_col, button_col = st.columns([8, 1.2], vertical_alignment="center")
    with input_col:
        question = st.text_input(
            "Ask your question",
            key="analyst_question_input",
            placeholder="For example: Which category has the biggest checkout-to-payment drop-off?",
            label_visibility="collapsed",
            max_chars=1000,
        )
    with button_col:
        submitted = st.form_submit_button("↑  Ask", type="primary", **STRETCH)

if submitted:
    q_clean = clean_question(question)
    limit_message = rate_limit_message()

    if len(q_clean) < 3:
        st.warning("Enter a question first.")
    elif limit_message:
        st.warning(limit_message)
    else:
        st.session_state["question_count"] = st.session_state.get("question_count", 0) + 1
        st.session_state["last_question_at"] = time.time()
        try:
            with st.spinner("Reviewing the data and preparing your analysis…"):
                result = answer_question(q_clean)

            if result["route"] is None:
                st.info(
                    "I can analyze retention, feature adoption, the category funnel, "
                    "category economics, experiments, daily metrics, and the product funnel. "
                    "You can also ask me to explain product growth and analytics concepts."
                )
            elif result["route"] == "product_education":
                st.markdown(
                    '<div class="answer-label">PRODUCT GROWTH EXPLAINED</div>',
                    unsafe_allow_html=True,
                )
                with st.container(border=True):
                    st.markdown(result["answer"] or "No explanation was returned.")
            elif result["evidence"] is None:
                st.info("The table for this topic has no rows yet, so there is nothing to analyze.")
            else:
                route, df = result["route"], result["df"]
                st.markdown('<div class="answer-label">ANALYST RESPONSE</div>', unsafe_allow_html=True)
                if result["missing"]:
                    st.warning(
                        f"{result['missing']} row(s) have missing numbers and show as n/a. "
                        "Rows with a missing value for the compared metric are left out of the headline."
                    )
                shown = render_card(route, df, q_clean)
                if shown:
                    st.markdown('<div class="answer-label">ANALYST COMMENTARY</div>', unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown(result["answer"] or "No answer was returned.")
                if result["unverified"]:
                    st.warning(
                        "Some numbers in the commentary were not found in the data: "
                        + ", ".join(result["unverified"])
                        + ". Check them against the table before you use them."
                    )
                with st.expander("Explore supporting data", expanded=False):
                    st.caption(f"Topic: {ROUTE_LABELS[route]}")
                    show_supporting_data(route, df)
        except Exception:
            logger.exception("Analysis failed")
            st.error("I couldn't complete that analysis. Check the app logs for the technical error, along with the "
                     "Databricks connection, warehouse status, table permissions, and AI function access.")
            st.caption("Do not share access tokens or Secrets values when troubleshooting.")
else:
    st.markdown("<div class='small-note'>Tip: ask one focused question at a time. The analyst will show its supporting data below the answer.</div>", unsafe_allow_html=True)
