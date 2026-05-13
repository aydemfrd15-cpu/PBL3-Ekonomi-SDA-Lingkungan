from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ============================================================
# Page setup
# ============================================================
st.set_page_config(
    page_title="Analisis Intertemporal Sumber Daya Emas",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

plt.style.use("dark_background")
plt.rcParams["figure.figsize"] = (8, 4)
plt.rcParams["axes.edgecolor"] = "white"
plt.rcParams["axes.linewidth"] = 1.2
plt.rcParams["font.size"] = 10


# ============================================================
# Helpers
# ============================================================
def fmt_idr(value: float) -> str:
    try:
        return f"Rp {value:,.2f}"
    except Exception:
        return str(value)


def fmt_num(value: float, digits: int = 2) -> str:
    try:
        return f"{value:,.{digits}f}"
    except Exception:
        return str(value)


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def make_line_figure(x, y, x_label, y_label, title=None):
    fig, ax = plt.subplots()
    ax.plot(x, y, marker="o")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def make_bar_figure(x, y, x_label, y_label, title=None):
    fig, ax = plt.subplots()
    ax.bar(x, y)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def reserve_status(price: float, mc: float) -> str:
    if price > mc:
        return "Reserve makin layak"
    if price < mc:
        return "Masih resource"
    return "Titik impas"


def depletion_period(df: pd.DataFrame):
    hit = df.index[df["Stock_Tersisa"] <= 0].tolist()
    if hit:
        return int(df.loc[hit[0], "Periode"])
    return None


def depletion_label(df: pd.DataFrame, horizon: int) -> str:
    dp = depletion_period(df)
    if dp is None:
        return f"> {horizon}"
    return str(dp)


def load_historical_data() -> pd.DataFrame:
    fallback = pd.DataFrame(
        {
            "Tahun": list(range(2014, 2025)),
            "Harga_Emas": [
                1264.99, 1215.69, 1249.03, 1293.40, 1309.30,
                1392.55, 1771.22, 1799.34, 1800.10, 1930.24, 2354.35
            ],
            "Produksi_Emas": [
                2342, 2210, 2207, 1967, 1957,
                1962, 1672, 1690, 1268, 1208, 1019
            ],
            "MC": [
                728.5, 772.2, 620.3, 822.8, 1529.2,
                1997.9, 1569.0, 2242.6, 2540.8, 2279.5, 3955.0
            ],
            "Stock_Emas": [
                805000.0, 804950.0, 804890.0, 804810.0, 804720.0,
                804620.0, 804500.0, 804340.0, 804150.0, 803880.0, 803520.0
            ],
        }
    )

    csv_path = Path("data_emas.csv")
    if not csv_path.exists():
        return fallback

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return fallback

    df.columns = [c.strip() for c in df.columns]

    rename_map = {}
    for col in df.columns:
        low = col.lower().strip()
        if low == "tahun":
            rename_map[col] = "Tahun"
        elif low in {"harga_emas", "harga emas", "harga"}:
            rename_map[col] = "Harga_Emas"
        elif low in {"stock_emas", "stok_emas", "stock emas", "stok emas", "stock"}:
            rename_map[col] = "Stock_Emas"
        elif low in {"produksi_emas", "produksi emas", "produksi", "q"}:
            rename_map[col] = "Produksi_Emas"
        elif low in {"mc", "marginal cost", "marginal_cost"}:
            rename_map[col] = "MC"

    df = df.rename(columns=rename_map)

    if "Tahun" not in df.columns or "Harga_Emas" not in df.columns:
        return fallback

    for col in ["Tahun", "Harga_Emas", "Stock_Emas", "Produksi_Emas", "MC"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Tahun", "Harga_Emas"]).copy()
    df["Tahun"] = df["Tahun"].astype(int)

    if "Stock_Emas" not in df.columns:
        start_stock = 805000.0
        end_stock = 803520.0
        if len(df) == 1:
            df["Stock_Emas"] = [start_stock]
        else:
            df["Stock_Emas"] = [
                start_stock + (end_stock - start_stock) * i / (len(df) - 1)
                for i in range(len(df))
            ]

    if "Produksi_Emas" not in df.columns:
        df["Produksi_Emas"] = pd.NA
    if "MC" not in df.columns:
        df["MC"] = pd.NA

    return df.sort_values("Tahun").reset_index(drop=True)


def simulate_market(
    structure: str,
    p0: float,
    mc0: float,
    lambda0: float,
    b0: float,
    reserve0: float,
    periods: int,
    n_firms: int,
    demand_growth: float,
    cost_growth: float,
    tech_improvement: float,
    depletion_penalty: float,
    r: float,
):
    rows = []
    stock = max(reserve0, 1.0)

    for t in range(periods + 1):
        depletion_ratio = 1.0 - (stock / reserve0 if reserve0 > 0 else 0.0)
        depletion_ratio = max(0.0, min(1.0, depletion_ratio))

        scarcity_rent = lambda0 * ((1.0 + r) ** t) * (1.0 + 0.35 * depletion_ratio)
        a_t = p0 * ((1.0 + demand_growth) ** t) + 0.20 * scarcity_rent

        effective_cost_growth = max(cost_growth - tech_improvement, -0.95)
        mc_t = mc0 * ((1.0 + effective_cost_growth) ** t) * (1.0 + depletion_penalty * depletion_ratio)

        if structure == "Persaingan Sempurna":
            q_t = max((a_t - mc_t) / b0, 0.0)
            q_t = min(q_t, stock)
            p_t = max(mc_t, a_t - b0 * q_t)

        elif structure == "Monopoli":
            q_t = max((a_t - mc_t) / (2.0 * b0), 0.0)
            q_t = min(q_t, stock)
            p_t = max(a_t - b0 * q_t, mc_t)

        elif structure == "Oligopoli":
            n = max(int(n_firms), 2)
            q_t = max((n * (a_t - mc_t)) / (b0 * (n + 1.0)), 0.0)
            q_t = min(q_t, stock)
            p_t = max(a_t - b0 * q_t, mc_t)

        else:
            raise ValueError("Struktur pasar tidak dikenali")

        stock_after = max(stock - q_t, 0.0)
        hotelling_price = mc_t + scarcity_rent

        rows.append(
            {
                "Periode": t,
                "Permintaan_Intersep": a_t,
                "MC_Efektif": mc_t,
                "Scarcity_Rent": scarcity_rent,
                "Harga_Benchmark_Hotelling": hotelling_price,
                "Output": q_t,
                "Harga": p_t,
                "Stock_Awal": stock,
                "Stock_Tersisa": stock_after,
                "Pendapatan": p_t * q_t,
                "Rasio_Deplesi": depletion_ratio,
            }
        )

        stock = stock_after

    return pd.DataFrame(rows)


# ============================================================
# Data
# ============================================================
data = load_historical_data()
data["Perubahan_Harga_%"] = data["Harga_Emas"].pct_change() * 100
data["Perubahan_Stock"] = data["Stock_Emas"].diff()
data["Perubahan_Stock_%"] = data["Stock_Emas"].pct_change() * 100

latest = data.iloc[-1]
prev = data.iloc[-2] if len(data) > 1 else latest
first = data.iloc[0]

latest_price = safe_float(latest["Harga_Emas"])
latest_stock = safe_float(latest["Stock_Emas"])
prev_price = safe_float(prev["Harga_Emas"])
prev_stock = safe_float(prev["Stock_Emas"])
first_price = safe_float(first["Harga_Emas"])
first_stock = safe_float(first["Stock_Emas"])

price_yoy = ((latest_price / prev_price) - 1) * 100 if prev_price else 0.0
stock_yoy = ((latest_stock / prev_stock) - 1) * 100 if prev_stock else 0.0
avg_price_growth = (
    ((latest_price / first_price) ** (1 / max(len(data) - 1, 1)) - 1) * 100
    if first_price
    else 0.0
)

# ============================================================
# Sidebar controls
# ============================================================
st.sidebar.title("Kontrol Simulasi")
st.sidebar.caption("Atur parameter supaya harga, output, dan stok benar-benar bergerak.")

st.sidebar.subheader("Parameter Pasar")
p0 = st.sidebar.slider("Harga Emas Antam (P0)", 1000.0, 6000.0, float(latest_price), 1.0)
mc0 = st.sidebar.slider("Biaya Marginal Awal (MC0)", 500.0, 5000.0, 1732.53, 10.0)
lambda0 = st.sidebar.slider("MUC Awal (λ0)", 1.0, 2000.0, max(float(latest_price - 1732.53), 50.0), 1.0)
r = st.sidebar.slider("Tingkat Diskonto (r)", 0.00, 0.20, 0.05, 0.005)
b0 = st.sidebar.slider("Koefisien Permintaan (b)", 0.100, 3.000, 0.788, 0.001)
n_firms = st.sidebar.slider("Jumlah Perusahaan Oligopoli", 2, 20, 4, 1)

with st.sidebar.expander("Parameter Lanjutan", expanded=False):
    sim_periods = st.slider("Horizon simulasi (periode)", 3, 20, 10, 1)
    reserve0 = st.slider("Cadangan awal (kg)", 100000.0, 2000000.0, 805000.0, 1000.0)
    demand_growth = st.slider("Pertumbuhan permintaan tahunan", 0.00, 0.20, 0.04, 0.005)
    cost_growth = st.slider("Kenaikan biaya tahunan", 0.00, 0.20, 0.03, 0.005)
    tech_improvement = st.slider("Efisiensi teknologi", 0.00, 0.20, 0.01, 0.005)
    depletion_penalty = st.slider("Tekanan kelangkaan terhadap biaya", 0.00, 0.50, 0.10, 0.01)
    green_tax = st.slider("Pajak karbon future ($)", 0.0, 100.0, 20.0, 1.0)

st.sidebar.divider()
st.sidebar.caption("Catatan: persaingan sempurna tidak memakai jumlah perusahaan. Jumlah perusahaan baru berpengaruh di oligopoli.")

# ============================================================
# CSS / Header / Cover
# ============================================================
st.markdown(
    """
<style>
.cover-wrapper{
    margin-top: 5px;
    margin-bottom: 24px;
    padding-left: 20px;
    padding-right: 20px;
}

.big-title {
    font-size: 78px;
    font-weight: 900;
    line-height: 1.02;
    letter-spacing: -2.5px;
    margin-top: 12px;
    margin-bottom: 12px;
    color: inherit;
    text-shadow: 0 0 18px rgba(255,255,255,0.05);
}

.subtitle-text {
    font-size: 24px;
    font-weight: 500;
    opacity: 0.68;
    margin-bottom: 26px;
    color: inherit;
}

.identity-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 28px;
    padding: 30px 38px 18px 38px;
    margin-top: 8px;
    backdrop-filter: blur(12px);
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02), 0 10px 35px rgba(0,0,0,0.35);
    max-width: 1100px;
}

.identity-box h3 {
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 28px;
    letter-spacing: -1px;
}

.identity-box p {
    font-size: 20px;
    line-height: 1.7;
    margin-bottom: 18px;
}

.identity-box hr {
    margin-top: 25px;
    margin-bottom: 30px;
    border: none;
    border-top: 1px solid rgba(255,255,255,0.10);
}

.logo-wrapper{
    display:flex;
    justify-content:center;
    align-items:flex-start;
    padding-top: 20px;
}

.logo-wrapper img{
    border-radius: 24px;
}

div[data-testid="stRadio"] > label {
    font-weight: 700;
}

/* =========================================================
MENU TAB HORIZONTAL
========================================================= */

div[role="radiogroup"]{
    display:flex;
    justify-content:flex-start;
    gap:14px;
    background:rgba(255,255,255,0.03);
    padding:12px 14px;
    border-radius:18px;
    border:1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(10px);
    margin-top:10px;
    margin-bottom:18px;
    overflow-x:auto;
}

div[role="radiogroup"] label{
    background:rgba(255,255,255,0.03);
    padding:10px 18px;
    border-radius:14px;
    border:1px solid rgba(255,255,255,0.06);
    transition:all 0.25s ease;
    font-weight:600;
}

div[role="radiogroup"] label:hover{
    background:rgba(244,197,66,0.12);
    border:1px solid rgba(244,197,66,0.35);
    transform:translateY(-2px);
}

div[role="radiogroup"] label p{
    font-size:15px;
}

/* tab aktif */

div[role="radiogroup"] input:checked + div{
    color:#F4C542 !important;
    font-weight:800 !important;
}

div[role="radiogroup"] label:has(input:checked){
    background:linear-gradient(
        135deg,
        rgba(244,197,66,0.18),
        rgba(244,197,66,0.05)
    );
    border:1px solid rgba(244,197,66,0.45);
    box-shadow:0 0 18px rgba(244,197,66,0.10);
}

</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="cover-wrapper">', unsafe_allow_html=True)
col1, col2 = st.columns([1.2, 4.5], gap="large")

with col1:
    st.markdown('<div class="logo-wrapper">', unsafe_allow_html=True)
    logo_path = Path("Logo Unisbaa.png")
    if logo_path.exists():
        st.image(str(logo_path), width=220)
    else:
        st.info("Logo Unisbaa.png belum ada di repo.")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        """
        <div class="big-title">
        Analisis Intertemporal<br>
        Sumber Daya <span style="color:#F4C542;">Emas</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            font-size:28px;
            font-weight:700;
            color:#F4C542;
            margin-top:-8px;
            margin-bottom:10px;
            letter-spacing:0.5px;
        ">
            PT Aneka Tambang Tbk (ANTAM)
        </div>

        <div class="subtitle-text">
            PBL 3 — Ekonomi Sumber Daya Alam dan Lingkungan
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="identity-box">
        <h3>Kelompok 4</h3>
        <p>
        <b>Salsa Zahratul Aulia</b> (10090224004)<br>
        <b>Aida Farida Kultsum</b> (10090224014)<br>
        <b>Nabil Athala Naufal</b> (10090224022)
        </p>
        <hr>
        <p>
        <b>Mata Kuliah:</b><br>
        Ekonomi Sumber Daya Alam dan Lingkungan
        </p>
        <p>
        <b>Dosen Pengampu:</b><br>
        YUHKA SUNDAYA, S.E., M.Si.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

st.info(
    "Dashboard ini merangkum data historis, simulasi harga sumber daya emas, dan analisis struktur pasar dengan tampilan yang lebih sederhana."
)

# ============================================================
# Parameter dasar
# ============================================================
st.subheader("📍 Parameter Dasar Analisis (T=0)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga Pasar", fmt_idr(p0))
c2.metric("Biaya Marginal", fmt_idr(mc0))
c3.metric("MUC Awal", fmt_idr(lambda0))
c4.metric("Suku Bunga", f"{r:.2%}")

# ============================================================
# Simulations
# ============================================================
sim_comp = simulate_market(
    "Persaingan Sempurna",
    p0=p0,
    mc0=mc0,
    lambda0=lambda0,
    b0=b0,
    reserve0=reserve0,
    periods=sim_periods,
    n_firms=n_firms,
    demand_growth=demand_growth,
    cost_growth=cost_growth,
    tech_improvement=tech_improvement,
    depletion_penalty=depletion_penalty,
    r=r,
)

sim_mono = simulate_market(
    "Monopoli",
    p0=p0,
    mc0=mc0,
    lambda0=lambda0,
    b0=b0,
    reserve0=reserve0,
    periods=sim_periods,
    n_firms=n_firms,
    demand_growth=demand_growth,
    cost_growth=cost_growth,
    tech_improvement=tech_improvement,
    depletion_penalty=depletion_penalty,
    r=r,
)

sim_oligo = simulate_market(
    "Oligopoli",
    p0=p0,
    mc0=mc0,
    lambda0=lambda0,
    b0=b0,
    reserve0=reserve0,
    periods=sim_periods,
    n_firms=n_firms,
    demand_growth=demand_growth,
    cost_growth=cost_growth,
    tech_improvement=tech_improvement,
    depletion_penalty=depletion_penalty,
    r=r,
)

sims = {
    "Persaingan": sim_comp,
    "Monopoli": sim_mono,
    "Oligopoli": sim_oligo,
}


# ============================================================
# Section menu
# ============================================================
section = st.radio(
    "",
    [
        "📊 Data & Cadangan",
        "📈 Analisis Hotelling",
        "🏛 Struktur Pasar",
        "📦 Simulasi Stok",
        "🌿 Green Paradox",
    ],
    horizontal=True,
)

st.markdown("---")

# ============================================================
# 1. Data & Cadangan
# ============================================================
if section == "📊 Data & Cadangan":
    st.header("Data Historis Produksi & Harga")

    left, right = st.columns([1, 1.1])

    with left:
        cols_show = ["Tahun", "Harga_Emas", "Stock_Emas"]
        if "Produksi_Emas" in data.columns:
            cols_show.append("Produksi_Emas")

        st.dataframe(data[cols_show], use_container_width=True, height=360)

    with right:
        fig_price = make_line_figure(data["Tahun"], data["Harga_Emas"], "Tahun", "Harga Emas", "Tren Harga Historis")
        st.pyplot(fig_price, use_container_width=True)

    st.caption("Harga emas naik saat kelangkaan dan ekspektasi pasar menguat, sedangkan stock bergerak turun karena ekstraksi berjalan terus.")

# ============================================================
# 2. Hotelling
# ============================================================
elif section == "📈 Analisis Hotelling":
    st.header("Model Optimasi Hotelling")

    years = []
    muc_values = []
    prices = []

    for t in range(sim_periods + 1):
        year = 2025 + t
        muc_t = lambda0 * ((1 + r) ** t)
        price_t = p0 * ((1 + demand_growth) ** t)

        years.append(year)
        muc_values.append(muc_t)
        prices.append(price_t)

    hotell_df = pd.DataFrame(
        {
            "Tahun": years,
            "MUC ($)": muc_values,
            "Harga ($)": prices,
        }
    )

    left, right = st.columns([1, 1.2])

    with left:
        st.dataframe(hotell_df, use_container_width=True, height=360)

    with right:
        fig, ax = plt.subplots()
        ax.plot(years, prices, marker="s", label="Harga Proyeksi")
        ax.plot(years, muc_values, linestyle="--", label="MUC")
        ax.set_title("Keseimbangan Nilai Intertemporal")
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)

    st.caption("Kalau tingkat diskonto naik, MUC naik lebih cepat. Dalam logika model, stok cenderung habis lebih cepat karena ekstraksi saat ini jadi lebih menarik.")

# ============================================================
# 3. Struktur Pasar
# ============================================================
elif section == "🏛 Struktur Pasar":
    st.header("Analisis Struktur Pasar")

    summary_rows = []
    for name, df in sims.items():
        summary_rows.append(
            {
                "Struktur": name,
                "Harga Awal": df.iloc[0]["Harga"],
                "Harga Akhir": df.iloc[-1]["Harga"],
                "Output Awal": df.iloc[0]["Output"],
                "Output Akhir": df.iloc[-1]["Output"],
                "Stock Akhir": df.iloc[-1]["Stock_Tersisa"],
                "Jangka Waktu Habis": depletion_label(df, sim_periods),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, height=180)

    st.markdown("### Ringkasan per struktur")
    a1, a2, a3 = st.columns(3)

    cards = [
        ("Persaingan", sim_comp, "Harga mengikuti biaya marginal."),
        ("Monopoli", sim_mono, "Output lebih kecil, harga lebih tinggi."),
        ("Oligopoli", sim_oligo, f"Jumlah perusahaan = {n_firms}, hasil bergeser di tengah."),
    ]

    for col, (name, df, note) in zip([a1, a2, a3], cards):
        with col:
            st.markdown(
                f"""
                <div style="padding:16px 18px;border-radius:18px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);min-height:170px;">
                    <h4 style="margin:0 0 12px 0;">{name}</h4>
                    <div style="margin-bottom:8px;"><b>Harga akhir:</b> {fmt_idr(df.iloc[-1]["Harga"])}</div>
                    <div style="margin-bottom:8px;"><b>Output akhir:</b> {fmt_num(df.iloc[-1]["Output"], 2)}</div>
                    <div style="margin-bottom:8px;"><b>Stock akhir:</b> {fmt_num(df.iloc[-1]["Stock_Tersisa"], 2)}</div>
                    <div style="opacity:0.8;"><b>Habis:</b> {depletion_label(df, sim_periods)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(note)

    chosen = st.selectbox("Lihat detail struktur", ["Persaingan", "Monopoli", "Oligopoli"])
    chosen_df = sims[chosen]

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Harga Awal", fmt_idr(chosen_df.iloc[0]["Harga"]))
    d2.metric("Harga Akhir", fmt_idr(chosen_df.iloc[-1]["Harga"]))
    d3.metric("Output Akhir", fmt_num(chosen_df.iloc[-1]["Output"], 2))
    d4.metric("Jangka Waktu Habis", depletion_label(chosen_df, sim_periods))

    left, right = st.columns(2)

    with left:
        st.dataframe(
            chosen_df[
                [
                    "Periode",
                    "Permintaan_Intersep",
                    "MC_Efektif",
                    "Scarcity_Rent",
                    "Harga_Benchmark_Hotelling",
                    "Output",
                    "Harga",
                    "Stock_Tersisa",
                ]
            ],
            use_container_width=True,
            height=360,
        )

    with right:
        fig_p, ax_p = plt.subplots()
        ax_p.plot(chosen_df["Periode"], chosen_df["Harga"], marker="o", label="Harga")
        ax_p.plot(chosen_df["Periode"], chosen_df["Harga_Benchmark_Hotelling"], marker="o", label="Benchmark Hotelling")
        ax_p.set_title(f"Jalur Harga — {chosen}")
        ax_p.legend()
        fig_p.tight_layout()
        st.pyplot(fig_p, use_container_width=True)

        fig_s, ax_s = plt.subplots()
        ax_s.plot(chosen_df["Periode"], chosen_df["Stock_Tersisa"], marker="o")
        ax_s.set_title(f"Jalur Stock — {chosen}")
        fig_s.tight_layout()
        st.pyplot(fig_s, use_container_width=True)

    st.caption("Logika mikroekonomi: persaingan paling dekat ke biaya marginal, monopoli paling tinggi harga dan paling rendah output, oligopoli berada di tengah.")

# ============================================================
# 4. Simulasi Stok
# ============================================================
elif section == "📦 Simulasi Stok":
    st.header("Simulasi Deplesi Stock Cadangan")

    depletion_df = pd.DataFrame(
        {
            "Struktur": list(sims.keys()),
            "Harga Akhir": [df.iloc[-1]["Harga"] for df in sims.values()],
            "Output Akhir": [df.iloc[-1]["Output"] for df in sims.values()],
            "Stock Akhir": [df.iloc[-1]["Stock_Tersisa"] for df in sims.values()],
            "Jangka Waktu Habis": [depletion_label(df, sim_periods) for df in sims.values()],
        }
    )
    st.dataframe(depletion_df, use_container_width=True, height=180)

    left, right = st.columns([1.25, 1])

    with left:
        fig, ax = plt.subplots()
        for name, df in sims.items():
            ax.plot(df["Periode"], df["Stock_Tersisa"], marker="o", label=name)
        ax.set_xlabel("Periode")
        ax.set_ylabel("Stock Tersisa")
        ax.set_title("Proyeksi Sisa Cadangan")
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)

    with right:
        chart_df = pd.DataFrame(
            {
                "Struktur": list(sims.keys()),
                "Tahun Habis": [
                    int(depletion_period(df)) if depletion_period(df) is not None else sim_periods + 1
                    for df in sims.values()
                ],
            }
        )
        fig2 = make_bar_figure(chart_df["Struktur"], chart_df["Tahun Habis"], "Struktur", "Tahun", "Jangka Waktu Habis")
        st.pyplot(fig2, use_container_width=True)

    st.caption("Kalau diskonto dinaikkan, harga dan MUC ikut naik lebih cepat, sehingga stok cenderung lebih cepat habis.")

# ============================================================
# 5. Green Paradox
# ============================================================
elif section == "🌿 Green Paradox":
    st.header("Analisis Green Paradox")

    baseline = sim_comp.copy()
    policy = sim_comp.copy()

    # Respons kebijakan: percepatan ekstraksi di awal, lalu tekanan setelahnya
    boost = 1.0 + (green_tax / 100.0) * 0.6
    cooling = 1.0 - (green_tax / 100.0) * 0.15

    policy["Output"] = [
        min(baseline.iloc[t]["Output"] * (boost if t <= sim_periods // 2 else cooling), baseline.iloc[t]["Stock_Awal"])
        for t in range(len(baseline))
    ]

    stock = reserve0
    policy_stock = []
    for t in range(len(policy)):
        stock = max(stock - policy.iloc[t]["Output"], 0.0)
        policy_stock.append(stock)
    policy["Stock_Tersisa"] = policy_stock

    left, right = st.columns([1.05, 1])

    with left:
        fig, ax = plt.subplots()
        ax.plot(baseline["Periode"], baseline["Output"], marker="o", label="Baseline")
        ax.plot(policy["Periode"], policy["Output"], marker="o", label="Dengan Kebijakan")
        ax.set_title("Respons Ekstraksi terhadap Sinyal Pajak Karbon")
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)

    with right:
        fig2, ax2 = plt.subplots()
        ax2.plot(baseline["Periode"], baseline["Stock_Tersisa"], marker="o", label="Baseline")
        ax2.plot(policy["Periode"], policy["Stock_Tersisa"], marker="o", label="Dengan Kebijakan")
        ax2.set_title("Dampak terhadap Stock")
        ax2.legend()
        fig2.tight_layout()
        st.pyplot(fig2, use_container_width=True)

    gp1, gp2, gp3 = st.columns(3)
    gp1.metric("Output awal baseline", fmt_num(baseline.iloc[0]["Output"], 2))
    gp2.metric("Output awal kebijakan", fmt_num(policy.iloc[0]["Output"], 2))
    gp3.metric("Stock akhir kebijakan", fmt_num(policy.iloc[-1]["Stock_Tersisa"], 2))

    st.caption(
        "Analisis green paradox: saat pasar mengantisipasi pajak karbon di masa depan, produsen cenderung mempercepat ekstraksi sekarang."
    )

st.markdown("---")
st.caption("Dashboard Analisis Ekonomi SDA | PBL 3 | FEB UNISBA | 2026")
