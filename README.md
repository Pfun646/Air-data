# Member Churn & Cancellation Insights: Streamlit dashboard

Two-page interactive dashboard (Executive overview, Retention deep-dive), built from the Power BI mock-up.

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py
```
Place `Customer_Loyalty_History.csv` and `Customer_Flight_Activity.csv` in the same folder as `app.py`
(or in a `data/` subfolder). If they are missing, the app shows upload boxes instead.

## Using it
- **Page switcher** under the title bar toggles between the two pages.
- **Filters (left pane)** apply to every KPI and chart: enrolment year, loyalty card, province, enrolment type, gender.
  "Reset filters" restores the defaults.
- Hover any chart for exact values, sample sizes and confidence intervals.

## Notes
- Filters work on member attributes. The year filter selects the **enrolment cohort** (cancellations are then those of that cohort, in any year).
- Rates use the 2013-2018 cohorts; the 2012 cohort has no recorded cancellations (see the analysis notebook).
- Small filtered groups give noisy rates; the province chart shows `n` and a 95% CI on hover.
- Files: `app.py` (the app), `.streamlit/config.toml` (colour theme), `requirements.txt`.
