from datetime import UTC, datetime

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

# Override by setting API_BASE to point at a remote host if needed
API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Multi-Model Router", layout="wide")


@st.cache_data(ttl=10)
def fetch_summary(window: str) -> dict | None:
    """Fetch aggregated metrics from the backend."""
    try:
        r = httpx.get(
            f"{API_BASE}/v1/metrics/summary",
            params={"window": window},
            timeout=5.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=10)
def fetch_requests(limit: int = 200) -> dict | None:
    """Fetch recent requests from the backend."""
    try:
        r = httpx.get(
            f"{API_BASE}/v1/requests",
            params={"limit": limit},
            timeout=5.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_health() -> bool:
    """Return True if the backend health endpoint responds OK."""
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Multi-Model Router")
    st.caption("Cost-aware LLM routing across Gemini tiers.")

    window = st.radio(
        "Time window",
        options=["1h", "24h", "7d", "30d"],
        index=1,
    )

    if st.button("Refresh"):
        st.cache_data.clear()

    healthy = fetch_health()
    if healthy:
        st.success("API connected")
    else:
        st.error("API unreachable")

# ── Guard: backend must be reachable ─────────────────────────────────────────

if not healthy:
    st.error(
        f"Backend unreachable at {API_BASE}. Is `make dev` running?"
    )
    st.stop()

# ── Fetch data ────────────────────────────────────────────────────────────────

summary = fetch_summary(window)
if summary is None:
    st.error(f"Failed to load metrics from {API_BASE}/v1/metrics/summary.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_overview, tab_explorer = st.tabs(["Overview", "Request Explorer"])

# ── Tab 1: Overview ───────────────────────────────────────────────────────────

with tab_overview:
    total_requests = summary.get("total_requests", 0)
    total_cost = float(summary.get("total_cost_usd", 0))
    avg_latency = summary.get("avg_latency_ms", 0.0)
    error_count = summary.get("error_count", 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Requests", total_requests)
    col2.metric("Total Spend (USD)", f"${total_cost:.6f}")
    col3.metric("Avg Latency (ms)", f"{avg_latency:.0f}")
    col4.metric("Error Count", error_count)

    if total_requests == 0:
        st.info("No requests yet. Hit POST /v1/route to generate data.")
    else:
        by_model = summary.get("by_model", [])
        if by_model:
            df_model = pd.DataFrame(by_model)
            df_model["total_cost_usd"] = df_model["total_cost_usd"].astype(float)
            df_model["avg_cost_usd"] = df_model["avg_cost_usd"].astype(float)
            df_model["avg_quality_score"] = pd.to_numeric(
                df_model["avg_quality_score"], errors="coerce"
            )

            st.subheader("Requests per model")
            fig_req = px.bar(
                df_model,
                x="model_name",
                y="request_count",
                labels={"model_name": "Model", "request_count": "Requests"},
            )
            st.plotly_chart(fig_req, use_container_width=True)

            st.subheader("Total cost per model (USD)")
            fig_cost = px.bar(
                df_model,
                x="model_name",
                y="total_cost_usd",
                labels={"model_name": "Model", "total_cost_usd": "Cost (USD)"},
            )
            st.plotly_chart(fig_cost, use_container_width=True)

            df_scatter = df_model.dropna(subset=["avg_quality_score"])
            if not df_scatter.empty:
                st.subheader("Cost vs quality")
                fig_scatter = px.scatter(
                    df_scatter,
                    x="avg_cost_usd",
                    y="avg_quality_score",
                    size="request_count",
                    color="model_name",
                    hover_data=["request_count", "avg_latency_ms"],
                    labels={
                        "avg_cost_usd": "Avg Cost (USD)",
                        "avg_quality_score": "Avg Quality Score",
                        "model_name": "Model",
                    },
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info(
                    "Quality scores not yet available. "
                    "Submit feedback via POST /v1/feedback to populate this chart."
                )

            st.subheader("Per-model metrics")
            st.dataframe(df_model, use_container_width=True)

# ── Tab 2: Request Explorer ───────────────────────────────────────────────────

with tab_explorer:
    requests_data = fetch_requests(limit=200)
    if requests_data is None:
        st.error(f"Failed to load requests from {API_BASE}/v1/requests.")
        st.stop()

    items = requests_data.get("items", requests_data) if isinstance(requests_data, dict) else requests_data
    if not items:
        st.info("No requests logged yet.")
    else:
        df_req = pd.DataFrame(items)

        display_cols = [
            c for c in [
                "request_id", "model_name", "classifier_label",
                "tokens_in", "tokens_out", "cost_usd",
                "latency_ms", "status", "created_at",
            ]
            if c in df_req.columns
        ]
        df_req = df_req[display_cols] if display_cols else df_req

        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            model_opts = ["All"] + sorted(df_req["model_name"].dropna().unique().tolist()) if "model_name" in df_req.columns else ["All"]
            model_filter = st.selectbox("Model", model_opts)

        with col_f2:
            label_opts = ["All"] + sorted(df_req["classifier_label"].dropna().unique().tolist()) if "classifier_label" in df_req.columns else ["All"]
            label_filter = st.selectbox("Complexity", label_opts)

        with col_f3:
            status_opts = ["All"] + sorted(df_req["status"].dropna().unique().tolist()) if "status" in df_req.columns else ["All"]
            status_filter = st.selectbox("Status", status_opts)

        df_filtered = df_req.copy()
        if model_filter != "All" and "model_name" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["model_name"] == model_filter]
        if label_filter != "All" and "classifier_label" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["classifier_label"] == label_filter]
        if status_filter != "All" and "status" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["status"] == status_filter]

        st.dataframe(df_filtered, use_container_width=True)

        st.download_button(
            label="Download CSV",
            data=df_filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"requests_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.csv",
            mime="text/csv",
        )
