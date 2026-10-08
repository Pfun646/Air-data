"""
Member Churn & Cancellation Insights - Streamlit dashboard
Two pages (Executive overview / Retention deep-dive), styled after the Power BI mock-up.

Run:  streamlit run app.py
Data: put Customer_Loyalty_History.csv and Customer_Flight_Activity.csv next to this file
      (or in ./data/), or upload them in the app.
"""
import io
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Member Churn & Cancellation Insights", page_icon="✈️",
                   layout="wide", initial_sidebar_state="expanded")

# ----------------------------------------------------------------------------- constants
BLUE, ORANGE, GREY, NAVY = "#118DFF", "#E66C37", "#C9CED6", "#12239E"
INK, MUTED, GRID = "#252423", "#605E5C", "#EDEBE9"
COHORT_COLOURS = ["#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#08519C", "#08306B"]
END = pd.Timestamp("2018-12-01")          # last month in the data
CLIFF = 8                                  # the month-8 cancellation spike
PAGES = ["Executive overview", "Retention deep-dive"]
LOYALTY_FILE, FLIGHTS_FILE = "Customer_Loyalty_History.csv", "Customer_Flight_Activity.csv"
PLOT_CFG = {"displayModeBar": False}
FONT = "Segoe UI, Helvetica Neue, Arial, sans-serif"

# ----------------------------------------------------------------------------- styling
st.markdown(f"""
<style>
  [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{ display: none !important; }}
  .block-container {{ padding: 0 1.4rem 1rem 1.4rem !important; max-width: 100% !important; }}
  .stApp {{ background: #F3F2F1; }}

  /* title bar */
  .hdr {{ background: #252423; margin: 0 -1.4rem 14px -1.4rem; padding: 0 1.4rem 0 1.6rem; height: 62px;
         display: flex; align-items: center; justify-content: space-between; border-left: 8px solid #F2C811; }}
  .hdr .ttl {{ color: #fff; font-size: 24px; font-weight: 700; font-family: {FONT}; }}
  .hdr .sub {{ color: #C8C6C4; font-size: 14px; font-family: {FONT}; }}

  /* filter pane */
  [data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid #E1DFDD; }}
  [data-testid="stSidebar"] > div:first-child {{ padding-top: 0.6rem; }}
  .fp-title {{ font-size: 12px; font-weight: 700; color: {MUTED}; letter-spacing: .08em; margin-bottom: 6px; }}
  [data-testid="stSidebar"] label p {{ font-size: 14px; }}
  [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ font-weight: 700; color: {INK}; }}

  /* page switcher */
  div[data-testid="stRadio"][class*="st-key-page"] label p {{ font-weight: 600; }}

  /* chart cards */
  [data-testid="stVerticalBlockBorderWrapper"] {{ background: #fff; border: 1px solid #E1DFDD !important;
         border-radius: 2px !important; box-shadow: none; }}
  .ctitle {{ font-size: 14px; font-weight: 700; color: {INK}; font-family: {FONT}; margin: 0 0 2px 2px; }}

  /* KPI cards */
  .kpi {{ background: #fff; border: 1px solid #E1DFDD; border-left: 5px solid var(--c); padding: 10px 12px 9px 14px;
         height: 108px; font-family: {FONT}; }}
  .kpi .l {{ font-size: 12.5px; color: {MUTED}; }}
  .kpi .v {{ font-size: 30px; font-weight: 700; color: {INK}; line-height: 1.25; }}
  .kpi .s {{ font-size: 11px; color: #8A8886; }}

  /* watch-list table */
  table.wl {{ width: 100%; border-collapse: collapse; font-family: {FONT}; font-size: 13px; margin-top: 8px; }}
  table.wl th {{ background: {BLUE}; color: #fff; text-align: left; padding: 9px 10px; font-weight: 700; }}
  table.wl td {{ padding: 9px 10px; color: {INK}; }}
  table.wl tr:nth-child(even) td {{ background: #F3F2F1; }}
  table.wl tr.tot td {{ font-weight: 700; }}
  .foot {{ text-align: center; font-size: 11px; color: #8A8886; margin-top: 10px; }}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------- data
def prepare(loyalty: pd.DataFrame, flights: pd.DataFrame):
    """Clean the raw files and derive churn fields (same logic as the analysis notebook)."""
    flights = flights.drop_duplicates()
    df = loyalty.copy()
    df.loc[df["Salary"] < 0, "Salary"] = np.nan
    df["enroll_date"] = pd.to_datetime(dict(year=df["Enrollment Year"], month=df["Enrollment Month"], day=1))
    df["cancel_date"] = pd.to_datetime(dict(year=df["Cancellation Year"], month=df["Cancellation Month"], day=1),
                                       errors="coerce")
    df["churned"] = df["cancel_date"].notna()
    stop = df["cancel_date"].fillna(END)
    df["tenure"] = (stop.dt.year - df["enroll_date"].dt.year) * 12 + (stop.dt.month - df["enroll_date"].dt.month)

    # flight rows for the 2017 enrolment cohort (used for the engagement profile on page 2)
    e17 = df.loc[df["Enrollment Year"] == 2017, ["Loyalty Number", "enroll_date", "churned", "tenure"]]
    fl = flights.merge(e17, on="Loyalty Number")
    fl["date"] = pd.to_datetime(dict(year=fl["Year"], month=fl["Month"], day=1))
    fl["m_since"] = (fl["date"].dt.year - fl["enroll_date"].dt.year) * 12 + (fl["date"].dt.month - fl["enroll_date"].dt.month)
    fl = fl[fl["m_since"].between(0, 8)][["Loyalty Number", "churned", "tenure", "m_since", "Total Flights"]]
    return df, fl


@st.cache_data(show_spinner="Loading data...")
def load_from_paths(lp, fp):
    return prepare(pd.read_csv(lp), pd.read_csv(fp))


@st.cache_data(show_spinner="Loading data...")
def load_from_bytes(lb, fb):
    return prepare(pd.read_csv(io.BytesIO(lb)), pd.read_csv(io.BytesIO(fb)))


def find_file(name):
    here = os.path.dirname(os.path.abspath(__file__))
    for folder in (here, os.path.join(here, "data"), ".", "data"):
        p = os.path.join(folder, name)
        if os.path.exists(p):
            return p
    return None


lp, fp = find_file(LOYALTY_FILE), find_file(FLIGHTS_FILE)
if lp and fp:
    DF, FL17 = load_from_paths(lp, fp)
else:
    st.markdown('<div class="hdr"><span class="ttl">Member Churn &amp; Cancellation Insights</span></div>',
                unsafe_allow_html=True)
    st.info("Data files not found next to the app. Upload both CSV files to continue.")
    up_l = st.file_uploader(LOYALTY_FILE, type="csv")
    up_f = st.file_uploader(FLIGHTS_FILE, type="csv")
    if not (up_l and up_f):
        st.stop()
    DF, FL17 = load_from_bytes(up_l.getvalue(), up_f.getvalue())


# ----------------------------------------------------------------------------- analysis helpers
def wilson_ci(k, n, z=1.96):
    p = k / n
    centre = (p + z ** 2 / (2 * n)) / (1 + z ** 2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / (1 + z ** 2 / n)
    return centre - half, centre + half


def hazard_table(d, tmax=36):
    """Share of members still active at the start of each tenure month who cancel in that month."""
    t = np.arange(tmax + 1)
    ten, ch = d["tenure"].to_numpy(), d["churned"].to_numpy()
    at_risk = np.array([(ten >= k).sum() for k in t])
    events = np.array([((ten == k) & ch).sum() for k in t])
    haz = np.where(at_risk > 0, events / np.maximum(at_risk, 1), np.nan)
    return pd.DataFrame({"at_risk": at_risk, "events": events, "hazard": haz}, index=t)


def yearly_table(f):
    rows = []
    for y in range(2013, 2019):
        start = pd.Timestamp(f"{y}-01-01")
        active_start = int(((f["enroll_date"] < start) & (~f["churned"] | (f["cancel_date"] >= start))).sum())
        new = int((f["Enrollment Year"] == y).sum())
        canc = int((f["Cancellation Year"] == y).sum())
        denom = active_start + new
        rows.append({"year": y, "enrolled": new, "cancelled": canc,
                     "cancel_rate": canc / denom if denom else np.nan})
    return pd.DataFrame(rows).set_index("year")


def rate_table(coh, col, order=None):
    rows = []
    for val, d in coh.groupby(col):
        k, n = int(d["churned"].sum()), len(d)
        lo, hi = wilson_ci(k, n)
        rows.append({"group": val, "rate": k / n, "lo": lo, "hi": hi, "n": n})
    out = pd.DataFrame(rows)
    return out


def fmt_pct(x, d=1):
    return "n/a" if x is None or pd.isna(x) else f"{x:.{d}%}"


# ----------------------------------------------------------------------------- UI building blocks
def kpi(col, label, value, sub, colour):
    col.markdown(f'<div class="kpi" style="--c:{colour}"><div class="l">{label}</div>'
                 f'<div class="v">{value}</div><div class="s">{sub}</div></div>', unsafe_allow_html=True)


def card(title):
    box = st.container(border=True)
    box.markdown(f'<div class="ctitle">{title}</div>', unsafe_allow_html=True)
    return box


def style(fig, height, show_legend=False, **layout):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=10, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED), showlegend=show_legend, hoverlabel=dict(font_size=12), **layout)
    fig.update_xaxes(showgrid=False, linecolor="#D2D0CE", ticks="", zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor="rgba(0,0,0,0)", ticks="", zeroline=False)
    return fig


def show(fig, key):
    st.plotly_chart(fig, width="stretch", config=PLOT_CFG, key=key)


# ----------------------------------------------------------------------------- charts
def fig_trend(yearly):
    fig = go.Figure()
    fig.add_bar(x=yearly.index, y=yearly["enrolled"], name="New enrolments", marker_color=BLUE,
                hovertemplate="%{x}: %{y:,} new enrolments<extra></extra>")
    fig.add_bar(x=yearly.index, y=yearly["cancelled"], name="Cancellations", marker_color=ORANGE,
                hovertemplate="%{x}: %{y:,} cancellations<extra></extra>")
    fig.add_scatter(x=yearly.index, y=yearly["cancel_rate"] * 100, name="Cancel rate (%)", yaxis="y2",
                    mode="lines+markers", line=dict(color=NAVY, width=3), marker=dict(size=8),
                    hovertemplate="%{x}: %{y:.2f}% cancel rate<extra></extra>")
    style(fig, 300, show_legend=True, barmode="group", bargap=0.25,
          legend=dict(orientation="h", x=0, y=1.13, font=dict(size=11)),
          yaxis2=dict(overlaying="y", side="right", range=[0, 6], ticksuffix="%", showgrid=False, ticks=""))
    fig.update_xaxes(type="category")
    return fig


def fig_tenure(tenure_counts):
    t = np.arange(0, 25)
    vals = tenure_counts.reindex(t, fill_value=0)
    fig = go.Figure(go.Bar(x=t, y=vals.values, marker_color=[ORANGE if k == CLIFF else GREY for k in t],
                           hovertemplate="Month %{x}: %{y:,} cancellations<extra></extra>"))
    if vals[CLIFF] > 0:
        fig.add_annotation(x=CLIFF, y=vals[CLIFF], text=f"<b>Month {CLIFF}: {int(vals[CLIFF]):,}</b>",
                           showarrow=True, arrowhead=2, arrowcolor=ORANGE, ax=70, ay=28,
                           font=dict(color=ORANGE, size=13))
    style(fig, 300)
    fig.update_xaxes(title="Tenure (months)", title_font_size=11, dtick=5)
    return fig


def fig_province(prov, overall):
    p = prov.sort_values("rate")
    colours = [ORANGE if (r.n >= 100 and r.lo > overall) else GREY for r in p.itertuples()]
    fig = go.Figure(go.Bar(
        x=p["rate"] * 100, y=p["group"], orientation="h", marker_color=colours,
        customdata=np.stack([p["n"], p["lo"] * 100, p["hi"] * 100], axis=1),
        hovertemplate="%{y}: %{x:.1f}% (95% CI %{customdata[1]:.1f}-%{customdata[2]:.1f}%, n=%{customdata[0]:,})<extra></extra>"))
    fig.add_vline(x=overall * 100, line_dash="dash", line_color=NAVY, line_width=1.3)
    style(fig, 300)
    fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID, range=[0, max(p["rate"].max() * 100 * 1.08, 1)])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return fig


def fig_card(cd, overall):
    fig = go.Figure(go.Bar(
        x=cd["group"], y=cd["rate"] * 100, marker_color=BLUE, width=0.55,
        text=[f"{v:.1%}" for v in cd["rate"]], textposition="outside", cliponaxis=False,
        customdata=cd["n"], hovertemplate="%{x}: %{y:.1f}% (n=%{customdata:,})<extra></extra>"))
    fig.add_hline(y=overall * 100, line_dash="dash", line_color=NAVY, line_width=1.3)
    style(fig, 300)
    fig.update_yaxes(ticksuffix="%", range=[0, max(18, cd["rate"].max() * 100 * 1.25)])
    return fig


def fig_hazard(haz):
    h = haz.loc[:24]
    fig = go.Figure(go.Bar(
        x=h.index, y=h["hazard"] * 100, marker_color=[ORANGE if k == CLIFF else GREY for k in h.index],
        customdata=np.stack([h["events"], h["at_risk"]], axis=1),
        hovertemplate="Month %{x}: %{y:.2f}% cancel (%{customdata[0]:,} of %{customdata[1]:,})<extra></extra>"))
    style(fig, 300)
    fig.update_xaxes(title="Tenure (months)", title_font_size=11, dtick=5)
    fig.update_yaxes(ticksuffix="%")
    return fig


def fig_survival(cohorts):
    fig = go.Figure()
    lowest = 100.0
    for (y, h), c in zip(cohorts.items(), COHORT_COLOURS[-len(cohorts):] if len(cohorts) else []):
        surv = (1 - h["hazard"].fillna(0)).cumprod() * 100
        ok = h.index[h["at_risk"] >= 100]
        if len(ok) == 0:
            continue
        last = int(ok.max())
        lowest = min(lowest, surv[:last + 1].min())
        fig.add_scatter(x=h.index[:last + 1], y=surv[:last + 1], mode="lines", name=str(y),
                        line=dict(color=c, width=3), hovertemplate=f"{y} cohort, month %{{x}}: %{{y:.1f}}% active<extra></extra>")
    fig.add_vline(x=CLIFF, line_dash="dash", line_color=ORANGE, line_width=1.3)
    style(fig, 300, show_legend=True, legend=dict(orientation="h", x=0, y=0.08, title_text="Enrolment year  ", font=dict(size=11)))
    fig.update_xaxes(title="Tenure (months)", title_font_size=11, dtick=5)
    fig.update_yaxes(ticksuffix="%", range=[min(80, np.floor(lowest) - 1), 100.5])
    return fig


def fig_cliff_by_cohort(cliff_rate):
    fig = go.Figure(go.Bar(
        x=[str(y) for y in cliff_rate.index], y=cliff_rate.values * 100, marker_color=BLUE, width=0.55,
        text=[fmt_pct(v) for v in cliff_rate.values], textposition="outside", cliponaxis=False,
        hovertemplate="%{x} cohort: %{y:.1f}% cancel at month 8<extra></extra>"))
    style(fig, 300)
    fig.update_yaxes(ticksuffix="%", range=[0, max(15, np.nanmax(cliff_rate.values) * 100 * 1.25) if len(cliff_rate) else 15])
    return fig


def fig_flights(prof):
    fig = go.Figure()
    for col, colour in (("Cancelled at month 8", ORANGE), ("Still active (never cancelled)", BLUE)):
        if col in prof:
            fig.add_scatter(x=prof.index, y=prof[col], name=col, mode="lines+markers",
                            line=dict(color=colour, width=3), marker=dict(size=8),
                            hovertemplate=f"{col}<br>Month %{{x}}: %{{y:.2f}} flights<extra></extra>")
    style(fig, 300, show_legend=True, legend=dict(orientation="h", x=0, y=1.13, font=dict(size=11)))
    fig.update_xaxes(title="Months since enrolment", title_font_size=11, dtick=1)
    fig.update_yaxes(rangemode="tozero")
    return fig


# ----------------------------------------------------------------------------- header + page switch
page = st.session_state.get("page", PAGES[0])
st.markdown(f'<div class="hdr"><span class="ttl">Member Churn &amp; Cancellation Insights</span>'
            f'<span class="sub">Page {PAGES.index(page) + 1} of 2 &nbsp;|&nbsp; {page}</span></div>',
            unsafe_allow_html=True)
st.radio("Page", PAGES, horizontal=True, key="page", label_visibility="collapsed")
page = st.session_state["page"]

# ----------------------------------------------------------------------------- filter pane (slicers)
with st.sidebar:
    st.markdown('<div class="fp-title">FILTERS</div>', unsafe_allow_html=True)
    year = st.radio("Enrolment year", ["All"] + [str(y) for y in range(2013, 2019)], key="f_year")
    st.markdown("**Loyalty card**")
    cards_sel = [c for c in ("Star", "Nova", "Aurora") if st.checkbox(c, value=True, key=f"f_card_{c}")]
    province = st.selectbox("Province", ["All"] + sorted(DF["Province"].unique()), key="f_prov")
    st.markdown("**Enrolment type**")
    types_sel = [t for t in ("Standard", "2018 Promotion") if st.checkbox(t, value=True, key=f"f_type_{t}")]
    st.markdown("**Gender**")
    gender_sel = [g for g in ("Female", "Male") if st.checkbox(g, value=True, key=f"f_gen_{g}")]
    if st.button("Reset filters", width="stretch"):
        for k in [k for k in st.session_state if k.startswith("f_")]:
            del st.session_state[k]
        st.rerun()

mask = (DF["Loyalty Card"].isin(cards_sel) & DF["Enrollment Type"].isin(types_sel) & DF["Gender"].isin(gender_sel))
if year != "All":
    mask &= DF["Enrollment Year"] == int(year)
if province != "All":
    mask &= DF["Province"] == province
F = DF[mask]

if F.empty:
    st.warning("No members match the current filters. Adjust the filters on the left.")
    st.stop()

# ----------------------------------------------------------------------------- shared calculations
COH = F[F["Enrollment Year"] >= 2013]                      # cohorts with complete cancellation records
total, cancelled = len(F), int(F["churned"].sum())
clv_total, clv_lost = F["CLV"].sum(), F.loc[F["churned"], "CLV"].sum()
canc = COH[COH["churned"]]
share8 = (canc["tenure"] == CLIFF).mean() if len(canc) else np.nan
n8 = int((canc["tenure"] == CLIFF).sum())

haz = hazard_table(COH)
cohorts = {y: hazard_table(COH[COH["Enrollment Year"] == y], tmax=24)
           for y in range(2013, 2019) if (COH["Enrollment Year"] == y).any()}
cliff_rate = pd.Series({y: h.loc[CLIFF, "hazard"] for y, h in cohorts.items()})

# watch list: active members 4-7 months in (1-4 months before the month-8 mark)
recent = [cohorts[y].loc[CLIFF, "hazard"] for y in (2017, 2018)
          if y in cohorts and cohorts[y].loc[CLIFF, "at_risk"] >= 30 and not pd.isna(cohorts[y].loc[CLIFF, "hazard"])]
rate_recent = float(np.mean(recent)) if recent else (haz.loc[CLIFF, "hazard"] if not pd.isna(haz.loc[CLIFF, "hazard"]) else 0.0)
watch = F[~F["churned"] & F["tenure"].between(4, 7)]
watch_card = (watch.groupby("Loyalty Card").agg(members=("CLV", "size"), clv=("CLV", "sum"))
              .reindex(["Aurora", "Nova", "Star"]).fillna(0))
watch_card["exp_cancel"] = watch_card["members"] * rate_recent
watch_card.loc["Total"] = watch_card.sum()
expected_leavers = len(watch) * rate_recent
expected_clv = watch["CLV"].sum() * rate_recent

overall = COH["churned"].mean() if len(COH) else 0.0

# =============================================================================== PAGE 1
if page == PAGES[0]:
    cols = st.columns(6)
    kpi(cols[0], "Total members", f"{total:,}", "enrolled 2012-2018", BLUE)
    kpi(cols[1], "Active members", f"{total - cancelled:,}", f"{(total - cancelled) / total:.1%} of all", BLUE)
    kpi(cols[2], "Cancelled members", f"{cancelled:,}", f"{cancelled / total:.1%} of all members", ORANGE)
    kpi(cols[3], "CLV of cancelled", f"${clv_lost / 1e6:,.1f}M", f"{clv_lost / clv_total:.1%} of total CLV", ORANGE)
    kpi(cols[4], "Cancel at month 8", fmt_pct(share8, 0), f"{n8:,} of {len(canc):,} cancellations", ORANGE)
    kpi(cols[5], "Watch list (4-7 mo.)", f"{len(watch):,}", f"~{expected_leavers:,.0f} expected to leave", NAVY)
    st.write("")

    c1, c2 = st.columns([1, 1])
    with c1, card("Enrolments vs. cancellations by year"):
        show(fig_trend(yearly_table(F)), "trend")
    with c2, card("Cancellations by months of membership"):
        show(fig_tenure(canc["tenure"].value_counts().sort_index()), "tenure")

    c3, c4, c5 = st.columns([1.25, 0.95, 0.95])
    with c3, card("Cancel rate by province"):
        show(fig_province(rate_table(COH, "Province"), overall), "prov")
    with c4, card("Cancel rate by loyalty card"):
        show(fig_card(rate_table(COH, "Loyalty Card"), overall), "card")
    with c5, card("Watch list: members approaching month 8"):
        rows = "".join(
            f'<tr class="{"tot" if name == "Total" else ""}"><td>{name}</td><td>{int(r.members):,}</td>'
            f'<td>{r.clv / 1e3:,.0f}</td><td>{r.exp_cancel:,.0f}</td></tr>' for name, r in watch_card.iterrows())
        st.markdown(f'<table class="wl"><tr><th>Card</th><th>Members</th><th>CLV ($K)</th><th>Exp. exits</th></tr>'
                    f'{rows}</table>', unsafe_allow_html=True)
        st.caption(f"Expected exits use the recent month-8 cancellation rate ({rate_recent:.1%}).")

# =============================================================================== PAGE 2
else:
    hz8 = haz.loc[CLIFF, "hazard"]
    hz_other = haz.drop(CLIFF).loc[:24, "hazard"].mean()
    multiple = hz8 / hz_other if hz_other and not pd.isna(hz8) else np.nan
    c13, c17 = cliff_rate.get(2013, np.nan), cliff_rate.get(2017, np.nan)

    cols = st.columns(6)
    kpi(cols[0], "Month-8 hazard", fmt_pct(hz8), "cancel in month 8, if still active", ORANGE)
    kpi(cols[1], "Hazard, other months", fmt_pct(hz_other, 2), "average, months 0-24", BLUE)
    kpi(cols[2], "Cliff multiple", "n/a" if pd.isna(multiple) else f"{multiple:,.0f}x", "month 8 vs. typical month", ORANGE)
    kpi(cols[3], "2013 cohort cliff", fmt_pct(c13), "cancel at month 8", BLUE)
    kpi(cols[4], "2017 cohort cliff", fmt_pct(c17), "cancel at month 8", ORANGE)
    kpi(cols[5], "Expected CLV at risk", f"${expected_clv / 1e6:,.1f}M", "watch-list members", NAVY)
    st.write("")

    c1, c2 = st.columns([1, 1])
    with c1, card("Monthly cancellation hazard by tenure"):
        show(fig_hazard(haz), "hazard")
    with c2, card("Share of cohort still active"):
        show(fig_survival(cohorts), "survival")

    # engagement profile: 2017 enrolees who cancelled at month 8 vs. those still active
    fl = FL17[FL17["Loyalty Number"].isin(F["Loyalty Number"])]
    leavers = fl[fl["churned"] & (fl["tenure"] == CLIFF)]
    stayers = fl[~fl["churned"]]
    prof = pd.DataFrame({
        "Cancelled at month 8": leavers.groupby("m_since")["Total Flights"].mean(),
        "Still active (never cancelled)": stayers.groupby("m_since")["Total Flights"].mean()})

    c3, c4 = st.columns([1, 1])
    with c3, card("Month-8 cancellation rate by enrolment cohort"):
        show(fig_cliff_by_cohort(cliff_rate), "cliff")
    with c4, card("Flights by month of membership (2017 enrolees)"):
        if prof.empty:
            st.info("No 2017 enrolees match the current filters.")
        else:
            show(fig_flights(prof), "flights")

st.markdown('<div class="foot">Data: loyalty programme 2012-2018 (Dec 2018 snapshot) &nbsp;|&nbsp; '
            'Rates use the 2013-2018 enrolment cohorts (the 2012 cohort has no recorded cancellations)</div>',
            unsafe_allow_html=True)
