import os
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


def reserve_status(price: float, mc: float) -> str:
    if price > mc:
        return "Reserve makin layak"
    if price < mc:
        return "Masih resource"
    return "Titik impas"


def load_historical_data() -> pd.DataFrame:
    """
    Prioritas:
    1. data_emas.csv kalau ada
    2. fallback bawaan supaya app tetap jalan
    """
    fallback = pd.DataFrame(
        {
            "Tahun": list(range(2014, 2025)),
            "Harga_Emas": [
                1264.99,
                1215.69,
                1249.03,
                1293.40,
                1309.30,
                1392.55,
                1771.22,
                1799.34,
                1800.10,
                1930.24,
                2354.35,
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
                805000.0,
                804950.0,
                804890.0,
                804810.0,
                804720.0,
                804620.0,
                804500.0,
                804340.0,
                804150.0,
                803880.0,
                803520.0,
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

    # Kalau stock belum ada, buat proxy sederhana supaya grafik tetap ada
    if "Stock_Emas" not in df.columns:
        start_stock = 805000.0
        end_stock = 803500.0
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
    a0: float,
    b0: float,
    mc0: float,
    reserve0: float,
    periods: int,
    n_firms: int,
    demand_growth: float,
    cost_growth: float,
    tech_improvement: float,
    depletion_penalty: float,
):
    """
    Simulasi dibuat agar:
    - angka berubah saat slider berubah
    - persaingan, monopoli, oligopoli punya rumus berbeda
    - stok berkurang dari waktu ke waktu
    """
    rows = []
    stock = max(reserve0, 1.0)

    for t in range(periods + 1):
        depletion_ratio = 1.0 - (stock / reserve0 if reserve0 > 0 else 0.0)
        depletion_ratio = max(0.0, min(1.0, depletion_ratio))

        # Demand makin tinggi saat kelangkaan naik
        a_t = a0 * ((1.0 + demand_growth) ** t) * (1.0 + 0.07 * depletion_ratio)

        # Biaya naik, teknologi menahan kenaikan itu
        effective_cost_growth = max(cost_growth - tech_improvement, -0.95)
        mc_t = mc0 * ((1.0 + effective_cost_growth) ** t) * (1.0 + depletion_penalty * depletion_ratio)

        # Rumus struktur pasar
        if structure == "Persaingan Sempurna":
            # P = MC; Q = (a - MC)/b
            q_t = max((a_t - mc_t) / b0, 0.0)
            q_t = min(q_t, stock)
            p_t = max(mc_t, a_t - b0 * q_t)

        elif structure == "Monopoli":
            # Q = (a - MC)/(2b); P = a - bQ
            q_t = max((a_t - mc_t) / (2.0 * b0), 0.0)
            q_t = min(q_t, stock)
            p_t = max(a_t - b0 * q_t, mc_t)

        elif structure == "Oligopoli":
            # Cournot symmetric:
            # Q = n(a-c)/(b(n+1))
            n = max(int(n_firms), 2)
            q_t = max((n * (a_t - mc_t)) / (b0 * (n + 1.0)), 0.0)
            q_t = min(q_t, stock)
            p_t = max(a_t - b0 * q_t, mc_t)

        else:
            raise ValueError("Struktur pasar tidak dikenali")

        rows.append(
            {
                "Periode": t,
                "Permintaan_Intersep": a_t,
                "MC_Efektif": mc_t,
                "Output": q_t,
                "Harga": p_t,
                "Stock_Tersisa": stock,
                "Pendapatan": p_t * q_t,
                "Rasio_Deplesi": depletion_ratio,
            }
        )

        stock = max(stock - q_t, 0.0)

    return pd.DataFrame(rows)


def structure_summary(df: pd.DataFrame) -> pd.Series:
    first = df.iloc[0]
    last = df.iloc[-1]
    return pd.Series(
        {
            "Harga Awal": first["Harga"],
            "Output Awal": first["Output"],
            "Stock Awal": first["Stock_Tersisa"],
            "Harga Akhir": last["Harga"],
            "Output Akhir": last["Output"],
            "Stock Akhir": last["Stock_Tersisa"],
            "Pendapatan Total": df["Pendapatan"].sum(),
        }
    )


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

# Parameter dasar dari laporan tugas
mc_default = 1732.53
reserve_default = 805000.0
a_default = float(data["Harga_Emas"].max())
b_default = 0.788
n_default = 4

# ============================================================
# Sidebar controls
# ============================================================
st.sidebar.title("Kontrol Simulasi")
st.sidebar.caption("Atur parameter supaya harga, output, dan stok benar-benar bergerak.")

structure_mode = st.sidebar.radio(
    "Struktur pasar yang ditampilkan",
    ["Persaingan Sempurna", "Monopoli", "Oligopoli"],
    index=0,
)

sim_periods = st.sidebar.slider("Horizon simulasi (periode)", 3, 20, 10, 1)
reserve0 = st.sidebar.slider("Cadangan awal (kg)", 100000.0, 2000000.0, reserve_default, 1000.0)
a0 = st.sidebar.slider("Intersep permintaan (a)", 1000.0, 6000.0, a_default, 1.0)
b0 = st.sidebar.slider("Koefisien permintaan (b)", 0.100, 3.000, b_default, 0.001)
mc0 = st.sidebar.slider("Biaya ekstraksi awal (MC)", 500.0, 5000.0, mc_default, 10.0)
n_firms = st.sidebar.slider("Jumlah perusahaan oligopoli", 2, 20, n_default, 1)
demand_growth = st.sidebar.slider("Pertumbuhan permintaan tahunan", 0.00, 0.20, 0.04, 0.005)
cost_growth = st.sidebar.slider("Kenaikan biaya tahunan", 0.00, 0.20, 0.03, 0.005)
tech_improvement = st.sidebar.slider("Efisiensi teknologi", 0.00, 0.20, 0.01, 0.005)
depletion_penalty = st.sidebar.slider("Tekanan kelangkaan terhadap biaya", 0.00, 0.50, 0.10, 0.01)

st.sidebar.divider()
st.sidebar.caption(
    "Catatan: pada persaingan sempurna harga mengikuti MC. "
    "Pada monopoli output lebih kecil. Pada oligopoli, jumlah perusahaan memengaruhi hasil."
)

# ============================================================
# CSS / Header / Cover
# ============================================================
st.markdown(
    """
<style>
.cover-wrapper{
    margin-top: 5px;
    margin-bottom: 34px;
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
    padding-top: 30px;
    padding-bottom: 12px;
    padding-left: 38px;
    padding-right: 38px;
    margin-top: 8px;
    backdrop-filter: blur(12px);
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.02),
        0 10px 35px rgba(0,0,0,0.35);
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

.small-note {
    font-size: 0.92rem;
    opacity: 0.82;
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
        <b>Aida Frida Kultsum</b> (10090224014)<br>
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
    "Dashboard ini menggabungkan data historis, kondisi pasar awal, simulasi harga sumber daya, "
    "serta mekanisme pasar persaingan, monopoli, dan oligopoli."
)

# ============================================================
# 1. Data kondisi pasar
# ============================================================
st.subheader("1. Data Kondisi Pasar (Diawal)")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Harga Emas Saat Ini", fmt_idr(latest_price), f"{price_yoy:+.2f}% yoy")
k2.metric("Stock Emas Saat Ini", fmt_num(latest_stock, 3), f"{stock_yoy:+.2f}% yoy")
k3.metric("Rata-rata Pertumbuhan Harga", f"{avg_price_growth:.2f}%")
k4.metric("Status Pasar", reserve_status(latest_price, mc_default))

st.write(
    "Harga yang naik sementara stock menurun menunjukkan tekanan kelangkaan. "
    "Di titik ini, emas makin kuat diposisikan sebagai aset bernilai tinggi."
)

# ============================================================
# 2. Data historis
# ============================================================
st.subheader("2. Data Historis")

hist_left, hist_right = st.columns([1.25, 1])
with hist_left:
    cols_show = ["Tahun", "Harga_Emas", "Stock_Emas"]
    if "Produksi_Emas" in data.columns:
        cols_show.append("Produksi_Emas")
    if "MC" in data.columns:
        cols_show.append("MC")

    st.dataframe(
        data[cols_show],
        use_container_width=True,
        height=380,
    )

with hist_right:
    st.markdown("**Ringkasan historis**")
    st.write(
        f"- Tahun awal: **{int(first['Tahun'])}**\n"
        f"- Tahun terakhir: **{int(latest['Tahun'])}**\n"
        f"- Harga awal: **{fmt_idr(first_price)}**\n"
        f"- Harga akhir: **{fmt_idr(latest_price)}**\n"
        f"- Stock awal: **{fmt_num(first_stock, 3)}**\n"
        f"- Stock akhir: **{fmt_num(latest_stock, 3)}**"
    )

    st.download_button(
        "Download Data Historis CSV",
        data=data[cols_show].to_csv(index=False).encode("utf-8"),
        file_name="data_historis_emas.csv",
        mime="text/csv",
    )

# ============================================================
# 3. Perkembangan harga emas
# ============================================================
st.subheader("3. Perkembangan Harga Emas")
fig1 = make_line_figure(data["Tahun"], data["Harga_Emas"], "Tahun", "Harga Emas")
st.pyplot(fig1, use_container_width=True)

st.write(
    "Grafik harga memperlihatkan arah perubahan harga emas dari waktu ke waktu. "
    "Naiknya harga biasanya sejalan dengan kelangkaan, ekspektasi pasar, dan biaya ekstraksi yang meningkat."
)

# ============================================================
# 4. Perubahan stock emas
# ============================================================
st.subheader("4. Perubahan Stock Emas")
fig2 = make_line_figure(data["Tahun"], data["Stock_Emas"], "Tahun", "Stock Emas")
st.pyplot(fig2, use_container_width=True)

st.write(
    "Perubahan stock menampilkan cadangan yang makin menipis. "
    "Dalam ekonomi sumber daya alam, ini menegaskan sifat emas sebagai depletable resource."
)

# ============================================================
# 5. Tabel perubahan stock
# ============================================================
st.subheader("5. Tabel Perhitungan Perubahan Stock Emas")
stock_change_table = data[["Tahun", "Stock_Emas", "Perubahan_Stock", "Perubahan_Stock_%"]].copy()
st.dataframe(stock_change_table, use_container_width=True, height=360)

st.caption("Perubahan negatif berarti stock berkurang dari periode sebelumnya.")

# ============================================================
# 6. Alat simulasi harga sumber daya
# ============================================================
st.subheader("6. Alat Simulasi Harga Sumber Daya")

st.write(
    "Simulasi di bawah ini dibuat supaya angka di tabel dan grafik benar-benar bergerak ketika parameter pasar diubah. "
    "Tiga mekanisme pasar dipisahkan: persaingan, monopoli, dan oligopoli."
)

sim_comp = simulate_market(
    "Persaingan Sempurna",
    a0=a0,
    b0=b0,
    mc0=mc0,
    reserve0=reserve0,
    periods=sim_periods,
    n_firms=n_firms,
    demand_growth=demand_growth,
    cost_growth=cost_growth,
    tech_improvement=tech_improvement,
    depletion_penalty=depletion_penalty,
)

sim_mono = simulate_market(
    "Monopoli",
    a0=a0,
    b0=b0,
    mc0=mc0,
    reserve0=reserve0,
    periods=sim_periods,
    n_firms=n_firms,
    demand_growth=demand_growth,
    cost_growth=cost_growth,
    tech_improvement=tech_improvement,
    depletion_penalty=depletion_penalty,
)

sim_oligo = simulate_market(
    "Oligopoli",
    a0=a0,
    b0=b0,
    mc0=mc0,
    reserve0=reserve0,
    periods=sim_periods,
    n_firms=n_firms,
    demand_growth=demand_growth,
    cost_growth=cost_growth,
    tech_improvement=tech_improvement,
    depletion_penalty=depletion_penalty,
)

sim_tabs = st.tabs(["Persaingan", "Monopoli", "Oligopoli", "Perbandingan"])

def render_simulation(df: pd.DataFrame, title: str, note: str):
    c1, c2, c3 = st.columns(3)
    c1.metric("Harga Awal", fmt_idr(df.iloc[0]["Harga"]))
    c2.metric("Output Awal", fmt_num(df.iloc[0]["Output"], 2))
    c3.metric("Stock Awal", fmt_num(df.iloc[0]["Stock_Tersisa"], 2))

    st.write(note)

    left, right = st.columns(2)
    with left:
        st.dataframe(
            df[
                [
                    "Periode",
                    "Permintaan_Intersep",
                    "MC_Efektif",
                    "Output",
                    "Harga",
                    "Stock_Tersisa",
                    "Pendapatan",
                    "Rasio_Deplesi",
                ]
            ],
            use_container_width=True,
            height=390,
        )

    with right:
        fig_p, ax_p = plt.subplots()
        ax_p.plot(df["Periode"], df["Harga"], marker="o")
        ax_p.set_xlabel("Periode")
        ax_p.set_ylabel("Harga")
        ax_p.set_title(f"Jalur Harga — {title}")
        fig_p.tight_layout()
        st.pyplot(fig_p, use_container_width=True)

        fig_s, ax_s = plt.subplots()
        ax_s.plot(df["Periode"], df["Stock_Tersisa"], marker="o")
        ax_s.set_xlabel("Periode")
        ax_s.set_ylabel("Stock Tersisa")
        ax_s.set_title(f"Jalur Stock — {title}")
        fig_s.tight_layout()
        st.pyplot(fig_s, use_container_width=True)

with sim_tabs[0]:
    st.markdown("### Mekanisme Pasar Persaingan")
    st.write(
        "Dalam persaingan sempurna, perusahaan adalah price taker. Harga cenderung mengikuti biaya marjinal, "
        "dan output menyesuaikan sampai pasar mencapai keseimbangan."
    )
    st.markdown(
        """
        **Logika mikroekonomi:**  
        \( P = MC \) sehingga output bergerak mengikuti titik pertemuan permintaan dan biaya marjinal.
        """
    )
    render_simulation(
        sim_comp,
        "Persaingan Sempurna",
        "Ketika stock mulai terbatas, harga bisa terdorong naik karena kelangkaan mulai terasa.",
    )

with sim_tabs[1]:
    st.markdown("### Mekanisme Pasar Monopoli")
    st.write(
        "Dalam monopoli, satu produsen menguasai pasar. Output cenderung lebih kecil dibanding persaingan, "
        "sedangkan harga lebih tinggi karena produsen punya kekuatan pasar."
    )
    st.markdown(
        """
        **Logika mikroekonomi:**  
        \( MR = MC \), lalu \( P = a - bQ \). Karena kurva permintaan turun, monopoli memproduksi lebih sedikit dan menjual lebih mahal.
        """
    )
    render_simulation(
        sim_mono,
        "Monopoli",
        "Monopoli biasanya menghasilkan output paling rendah dan harga paling tinggi pada parameter yang sama.",
    )

with sim_tabs[2]:
    st.markdown("### Mekanisme Pasar Oligopoli")
    st.write(
        "Dalam oligopoli, beberapa perusahaan saling bereaksi satu sama lain. Semakin banyak perusahaan, "
        "hasilnya makin mendekati persaingan sempurna."
    )
    st.markdown(
        """
        **Logika mikroekonomi:**  
        Model Cournot dipakai agar jumlah perusahaan benar-benar memengaruhi output.  
        Makin banyak perusahaan, output total naik dan harga turun.
        """
    )
    render_simulation(
        sim_oligo,
        "Oligopoli",
        "Jumlah perusahaan di sini benar-benar memengaruhi output dan harga melalui formula Cournot.",
    )

with sim_tabs[3]:
    st.markdown("### Perbandingan Tiga Mekanisme Pasar")
    summary_df = pd.DataFrame(
        {
            "Persaingan": structure_summary(sim_comp),
            "Monopoli": structure_summary(sim_mono),
            "Oligopoli": structure_summary(sim_oligo),
        }
    )
    st.dataframe(summary_df, use_container_width=True)

    st.write(
        "Secara mikroekonomi, urutannya biasanya: harga persaingan paling rendah, monopoli paling tinggi, "
        "dan oligopoli berada di tengah."
    )

st.success(
    "Simulasi sudah menghubungkan parameter pasar dengan tabel dan grafik, sehingga perubahan slider langsung mengubah hasil."
)
