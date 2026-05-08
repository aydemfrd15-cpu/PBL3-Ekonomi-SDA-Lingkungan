import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Analisis Intertemporal Sumber Daya Emas",
    page_icon="🟡",
    layout="wide",
)

# -----------------------------
# Helper functions
# -----------------------------
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

# -----------------------------
# Load data
# -----------------------------
try:
    data = pd.read_csv("data_emas.csv")
except Exception as e:
    st.error(f"Gagal membaca data_emas.csv: {e}")
    st.stop()

data.columns = [c.strip() for c in data.columns]

# Be tolerant to column naming variations
rename_map = {}
for col in data.columns:
    if col.lower() == "tahun":
        rename_map[col] = "Tahun"
    elif col.lower() in ("harga_emas", "harga emas"):
        rename_map[col] = "Harga_Emas"
    elif col.lower() in ("stock_emas", "stok_emas", "stock emas", "stok emas"):
        rename_map[col] = "Stock_Emas"
data = data.rename(columns=rename_map)

required_cols = {"Tahun", "Harga_Emas", "Stock_Emas"}
missing = required_cols - set(data.columns)
if missing:
    st.error(
        "Kolom wajib pada data_emas.csv belum lengkap. "
        f"Yang masih kurang: {', '.join(sorted(missing))}"
    )
    st.stop()

for col in ["Tahun", "Harga_Emas", "Stock_Emas"]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data = data.dropna(subset=["Tahun", "Harga_Emas", "Stock_Emas"]).copy()
data["Tahun"] = data["Tahun"].astype(int)
data = data.sort_values("Tahun").reset_index(drop=True)

# Derived historical columns
data["Perubahan_Harga_%"] = data["Harga_Emas"].pct_change() * 100
data["Perubahan_Stock"] = data["Stock_Emas"].diff()
data["Perubahan_Stock_%"] = data["Stock_Emas"].pct_change() * 100

latest = data.iloc[-1]
prev = data.iloc[-2] if len(data) > 1 else latest
first = data.iloc[0]

latest_price = float(latest["Harga_Emas"])
latest_stock = float(latest["Stock_Emas"])
prev_price = float(prev["Harga_Emas"])
prev_stock = float(prev["Stock_Emas"])
first_price = float(first["Harga_Emas"])

price_yoy = ((latest_price / prev_price) - 1) * 100 if prev_price else 0
stock_yoy = ((latest_stock / prev_stock) - 1) * 100 if prev_stock else 0
avg_price_growth = ((latest_price / first_price) ** (1 / max(len(data) - 1, 1)) - 1) * 100 if first_price else 0
total_stock_change = latest_stock - float(first["Stock_Emas"])

# Practical report anchors used as default parameters
a_default = 2977.841
b_default = 0.788
mc_default = 1732.53
r_default = 0.05
T_default = 10

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Identitas Penelitian")
st.sidebar.write("""
PBL 3 - Ekonomi SDA & Lingkungan

Topik:
Depletable Resource Allocation (Emas)

Universitas Islam Bandung
""")

scenario = st.sidebar.radio("Scenario", ["Pesimis", "Moderat", "Optimis"], index=1)

st.sidebar.subheader("Parameter Simulasi")
discount_rate = st.sidebar.slider("Tingkat bunga / diskonto (r)", 0.0, 0.20, r_default, 0.005)
horizon = st.sidebar.slider("Horizon simulasi (tahun)", 3, 15, T_default, 1)
mc_value = st.sidebar.slider("Biaya ekstraksi rata-rata / MC", 500.0, 4000.0, mc_default, 10.0)
tech_improvement = st.sidebar.slider("Perbaikan teknologi (%)", 0.0, 30.0, 10.0, 0.5)
reg_intensity = st.sidebar.slider("Intensitas regulasi hijau (%)", 0.0, 100.0, 20.0, 1.0)

with st.sidebar.expander("Parameter Struktur Pasar", expanded=False):
    a = st.slider("Intersep permintaan (a)", 1000.0, 5000.0, a_default, 1.0)
    b = st.slider("Slope permintaan (b)", 0.100, 2.500, b_default, 0.001)
    oligopoly_firms = st.slider("Jumlah perusahaan oligopoli", 2, 10, 4, 1)

scenario_factor = {"Pesimis": 0.95, "Moderat": 1.00, "Optimis": 1.08}[scenario]
market_price_now = latest_price * scenario_factor
market_stock_now = latest_stock

current_status = "Reserve makin layak" if market_price_now >= mc_value else "Masih resource"
market_signal = "Bullish / scarcity naik" if price_yoy > 0 and stock_yoy < 0 else "Mixed / transisi"

# -----------------------------
# Title and quick intro
# -----------------------------
st.image(
    "https://upload.wikimedia.org/wikipedia/id/5/56/Logo_Unisba.png",
    width=120
)
st.title("Analisis Intertemporal Sumber Daya Emas")
st.markdown("""
### Informasi Pengembang
Dikembangkan oleh:
- Salsa Zahratul Aulia (10090224004)
- Aida Frida Kultsum (10090224014)
- Nabil Athala Naufal (10090224022)
Pada Mata Kuliah:
**Ekonomi Sumber Daya Alam dan Lingkungan**

Di bawah bimbingan:
**YUHKA SUNDAYA, S.E., M.SI.**
""")

st.caption("PBL 3 - Depletable Resource Allocation | Dashboard simulasi harga, cadangan, Hotelling, dan Green Paradox")

st.write("""
Dashboard ini menggabungkan data historis, kondisi pasar saat ini, simulasi Hotelling murni,
simulasi Green Paradox, spektrum cadangan, dan mekanisme struktur pasar untuk menjelaskan
alokasi intertemporal sumber daya depletable.
""")

# -----------------------------
# Start: current market and historical data
# -----------------------------
st.subheader("1. Data Kondisi Pasar Saat Ini")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Harga Emas Saat Ini", fmt_idr(market_price_now), f"{price_yoy:+.2f}% yoy")
k2.metric("Stock Emas Saat Ini", fmt_num(market_stock_now, 3), f"{stock_yoy:+.2f}% yoy")
k3.metric("MC Rata-rata Praktikum", fmt_idr(mc_default), f"MC simulasi {fmt_idr(mc_value)}")
k4.metric("Status Pasar", current_status, market_signal)

st.write("""
Kondisi pasar saat ini menunjukkan bahwa harga emas berada dalam tren naik
sementara stock terus menurun. Kombinasi ini menandakan tekanan kelangkaan yang makin kuat.

Jika harga pasar berada di atas biaya ekstraksi, maka sumber daya semakin layak
dikategorikan sebagai reserve secara ekonomis.

Dalam perspektif intertemporal, kenaikan harga mencerminkan meningkatnya scarcity value
dan ekspektasi nilai sumber daya di masa depan.
""")

st.info(
    f"Pada kondisi scenario **{scenario}**, harga saat ini diposisikan pada {fmt_idr(market_price_now)} "
    f"dan stock terakhir {fmt_num(market_stock_now, 3)}. Harga yang berada di atas MC menunjukkan "
    "bahwa sumber daya semakin layak menjadi reserve secara ekonomis."
)

st.subheader("2. Data Historis")
st.dataframe(data[["Tahun", "Harga_Emas", "Stock_Emas"]], use_container_width=True)

st.download_button(
    "Download Data Historis CSV",
    data=data[["Tahun", "Harga_Emas", "Stock_Emas"]].to_csv(index=False).encode("utf-8"),
    file_name="data_historis_emas.csv",
    mime="text/csv",
)

# -----------------------------
# Price development
# -----------------------------
st.subheader("3. Perkembangan Harga Emas")
fig1, ax1 = plt.subplots()
ax1.plot(data["Tahun"], data["Harga_Emas"], marker="o")
ax1.set_xlabel("Tahun")
ax1.set_ylabel("Harga Emas")
st.pyplot(fig1)

st.write("""
Grafik harga memperlihatkan tren kenaikan dalam jangka panjang. Kenaikan harga merefleksikan
scarcity value, ekspektasi masa depan, dan peran emas sebagai aset lindung nilai.
""")

# -----------------------------
# Stock development
# -----------------------------
st.subheader("4. Perubahan Stock Emas")
fig2, ax2 = plt.subplots()
ax2.plot(data["Tahun"], data["Stock_Emas"], marker="o")
ax2.set_xlabel("Tahun")
ax2.set_ylabel("Stock Emas")
st.pyplot(fig2)

st.write("""
Penurunan stock emas menunjukkan bahwa sumber daya terus diekstraksi dan cadangan fisik
semakin menurun. Dalam ekonomi sumber daya alam, tren ini menegaskan karakter emas sebagai
depletable resource.
""")

st.subheader("5. Tabel Perhitungan Perubahan Stock Emas")
stock_change_table = data[["Tahun", "Stock_Emas", "Perubahan_Stock", "Perubahan_Stock_%"]].copy()
st.dataframe(stock_change_table, use_container_width=True)

st.write("""
Kolom perubahan stock membantu melihat seberapa cepat cadangan berkurang dari tahun ke tahun.
Perubahan negatif yang konsisten menunjukkan tekanan kelangkaan yang makin kuat.
""")

# -----------------------------
# SIMULASI HARGA SUMBER DAYA
# -----------------------------
st.subheader("2A. Alat Simulasi Harga Sumber Daya")

st.write("""
Bagian ini digunakan untuk mensimulasikan harga sumber daya emas
berdasarkan biaya ekstraksi, tingkat diskonto, dan kondisi pasar.
Simulasi ini membantu membaca bagaimana harga bergerak dalam kerangka intertemporal.
""")

sim_col1, sim_col2, sim_col3 = st.columns(3)

with sim_col1:
    sim_mc = st.slider("Biaya ekstraksi (MC) simulasi", 500.0, 4000.0, mc_default, 10.0)
with sim_col2:
    sim_r = st.slider("Tingkat bunga / diskonto (r)", 0.0, 0.20, r_default, 0.005)
with sim_col3:
    sim_years = st.slider("Horizon simulasi", 3, 15, T_default, 1)

sim_price0 = max(first_price, sim_mc)
sim_prices = [sim_price0 * ((1 + sim_r) ** t) for t in range(sim_years + 1)]
sim_df = pd.DataFrame({
    "Tahun": list(range(sim_years + 1)),
    "Harga Simulasi": sim_prices
})

sim_c1, sim_c2 = st.columns(2)
with sim_c1:
    st.dataframe(sim_df, use_container_width=True)
with sim_c2:
    fig_sim, ax_sim = plt.subplots()
    ax_sim.plot(sim_df["Tahun"], sim_df["Harga Simulasi"], marker="o")
    ax_sim.set_xlabel("Tahun")
    ax_sim.set_ylabel("Harga Simulasi")
    st.pyplot(fig_sim)

st.write("""
Jika tingkat diskonto meningkat, jalur harga simulasi menjadi lebih cepat naik.
Ini memperkuat logika Hotelling bahwa sumber daya depletable memiliki nilai waktu.
""")

# -----------------------------
# BAB I
# -----------------------------
st.divider()
st.subheader("BAB I. Pendahuluan")

st.markdown("### 1.1 Latar Belakang")

st.write("""
Emas merupakan salah satu komoditas sumber daya alam tidak terbarukan (depletable resources) yang memiliki nilai ekonomi tinggi dalam sistem perekonomian global. Nilai emas tidak hanya terbentuk dari fungsi fisiknya 
sebagai komoditas tambang, tetapi juga dari konstruksi sosial dan makna yang diberikan manusia terhadap komoditas tersebut. Menurut perspektif The Sense of Beauty yang dikemukakan oleh George Santayana, 
nilai muncul akibat preferensi dan kebutuhan manusia terhadap suatu objek. Dalam konteks ekonomi modern, emas dipandang sebagai aset yang mampu menjaga 
kestabilan nilai, berfungsi sebagai instrumen lindung inflasi (hedging asset), serta menjadi simbol keamanan finansial di tengah ketidakpastian ekonomi global.
Persepsi ini menyebabkan permintaan terhadap emas tetap tinggi dan membentuk ekspektasi bahwa emas akan terus memiliki nilai ekonomi di masa depan.

Sebagai sumber daya yang terbatas, emas menghadapi tantangan deplesi akibat 
aktivitas ekstraksi yang berkelanjutan. Berdasarkan data industri emas ANTAM 
periode 2014–2024, harga emas meningkat dari USD 1.264,99 menjadi USD 2.354,35, 
sementara volume produksi menurun dari 2.342 kg menjadi 1.019 kg.
Pada periode yang sama, nilai marginal cost (MC) meningkat dari sekitar 728,5 
menjadi 3.955. Secara ekonomi, kondisi ini menunjukkan bahwa proses ekstraksi 
emas menjadi semakin mahal akibat berkurangnya cadangan yang mudah diakses 
dan meningkatnya biaya operasional.
Fenomena ini menunjukkan bahwa peningkatan nilai ekonomi emas tidak selalu 
diikuti oleh peningkatan kapasitas produksi, melainkan dapat mencerminkan 
meningkatnya kelangkaan sumber daya.

Kondisi ini menimbulkan dilema intertemporal dalam pengelolaan sumber daya alam, 
yaitu pertukaran antara keuntungan ekonomi jangka pendek dan keberlanjutan 
nilai ekonomi di masa depan.
Ketika harga emas meningkat, perusahaan terdorong untuk mempercepat ekstraksi 
guna memperoleh rente sumber daya (resource rent) yang lebih besar. Namun, 
eksploitasi yang terlalu agresif dapat mempercepat penurunan cadangan dan 
meningkatkan biaya ekstraksi pada periode berikutnya.
Dalam perspektif ekonomi sumber daya alam, keputusan ekstraksi dipengaruhi 
tidak hanya oleh kondisi pasar saat ini, tetapi juga oleh ekspektasi terhadap 
nilai ekonomi di masa depan.
Oleh karena itu, pengelolaan emas memerlukan alokasi sumber daya antarwaktu 
yang efisien agar kepentingan generasi saat ini tidak mengorbankan potensi 
manfaat ekonomi bagi generasi mendatang.

Berdasarkan uraian tersebut, penelitian ini bertujuan untuk menganalisis 
bagaimana dinamika harga, biaya produksi, dan keputusan ekstraksi emas 
mencerminkan persoalan efisiensi alokasi intertemporal.
Penelitian ini juga bertujuan untuk memahami peran persepsi manusia dan 
mekanisme pasar dalam membentuk nilai ekonomi emas, serta mengevaluasi 
strategi pengelolaan ekstraksi yang lebih efisien dan berkelanjutan di tengah 
keterbatasan cadangan sumber daya alam.
""")

st.markdown("### 1.2 Rumusan Masalah")
st.write("""
1. Bagaimana dinamika perubahan harga dan teknologi memengaruhi pergeseran status cadangan
   (resource ke reserve) pada komoditas ini?
2. Apakah jalur ekstraksi yang berjalan saat ini sudah memenuhi kondisi efisiensi alokasi
   intertemporal sesuai Aturan Hotelling?
3. Bagaimana potensi distorsi pasar atau fenomena Green Paradox dapat terjadi akibat rencana
   kebijakan lingkungan di masa depan?
""")

st.markdown("### 1.3 Tujuan Penelitian")
st.write("""
Menemukan pola alokasi terbaik yang menyeimbangkan antara kebutuhan ekonomi jangka pendek
dan keberlanjutan nilai di masa depan.
""")

# -----------------------------
# BAB II
# -----------------------------
st.subheader("BAB II. Tinjauan Pustaka dan Landasan Teoritis")

st.markdown("### 2.1 Konsep Nilai dan Ekspektasi Waktu (Perspektif Santayana)")
st.write("""
Keputusan optimal alokasi sumber daya tidak sepenuhnya objektif, melainkan dipengaruhi persepsi,
ekspektasi harga, dan cara manusia menilai risiko masa depan.
""")

st.markdown("### 2.2 Taksonomi Cadangan")
st.write("""
Resources adalah total sumber daya, sedangkan reserves adalah bagian yang layak secara ekonomis
untuk ditambang. Perubahan harga, teknologi, dan biaya ekstraksi dapat menggeser status resource
menjadi reserve.
""")

st.markdown("### 2.3 Model Alokasi Intertemporal dan Aturan Hotelling")
st.write("""
Aturan Hotelling menyatakan bahwa harga bersih sumber daya depletable harus tumbuh sejalan
dengan tingkat bunga, atau secara sederhana dP/dt = rP.
""")

st.markdown("### 2.4 Eksternalitas Lingkungan dan Green Paradox")
st.write("""
Jika biaya sosial tidak masuk ke harga pasar, maka terjadi kegagalan pasar. Ketika regulasi hijau
diumumkan, produsen dapat mempercepat ekstraksi sebelum kebijakan berlaku. Inilah Green Paradox.
""")

# -----------------------------
# BAB III
# -----------------------------
st.subheader("BAB III. Metodologi Penelitian")

st.markdown("### 3.1 Jenis dan Sumber Data")
st.write("""
Data yang digunakan berupa data sekunder dari praktikum sebelumnya, yaitu tren harga komoditas,
estimasi biaya ekstraksi, hasil regresi permintaan emas, simulasi alokasi dinamis, dan estimasi
umur cadangan.
""")

st.markdown("### 3.2 Tahapan Analisis Simulasi")
st.write("""
1. Tahap Simulasi Cadangan: mengamati perubahan kelayakan ekonomi ketika harga dan biaya berubah.
2. Tahap Proyeksi Hotelling: membandingkan jalur harga dengan prinsip pertumbuhan harga bersih sumber daya.
3. Tahap Skenario Kebijakan: mensimulasikan dampak regulasi hijau terhadap keputusan ekstraksi.
""")

# -----------------------------
# IMPLEMENTASI TEKNIS
# -----------------------------
st.subheader("Implementasi Teknis")

tech1, tech2 = st.columns(2)

with tech1:
    st.success("Coding menggunakan GitHub")
    st.write("""
    Seluruh kode disimpan dalam repository GitHub agar versi program terdokumentasi,
    mudah diperbarui, dan dapat dihubungkan langsung ke Streamlit Cloud.
    """)

with tech2:
    st.info("Display user interface dengan Streamlit")
    st.write("""
    Streamlit digunakan untuk menampilkan data historis, grafik, simulasi harga,
    mekanisme pasar, dan interpretasi ekonomi dalam satu antarmuka interaktif.
    """)

# -----------------------------
# BAB IV
# -----------------------------
st.subheader("BAB IV. Hasil dan Pembahasan")

# 4.1 reserve spectrum proxy / current market interpretation
st.markdown("### 4.1 Analisis Pergeseran Spektrum Cadangan")
st.write("""
Hasil praktikum sebelumnya menunjukkan bahwa kenaikan harga emas dan perubahan biaya produksi
dapat mengubah sumber daya yang semula belum ekonomis menjadi cadangan yang layak ditambang.
Kondisi ini menegaskan bahwa batas antara resource dan reserve bersifat dinamis karena dipengaruhi
harga pasar, teknologi, dan biaya ekstraksi.
""")

# 4.1.1 Reserve spectrum simulation
st.markdown("#### Simulasi Spektrum Cadangan")
tech_factor = 1 - (tech_improvement / 100)
effective_mc_series = mc_value * (tech_factor ** (data.index / max(len(data)-1, 1)))
reserve_score = ((data["Harga_Emas"] - effective_mc_series) / effective_mc_series).clip(lower=0, upper=1.5)
reserve_volume = data["Stock_Emas"] * reserve_score.clip(upper=1.0)

reserve_table = pd.DataFrame({
    "Tahun": data["Tahun"],
    "Harga_Emas": data["Harga_Emas"],
    "MC_Efektif": effective_mc_series,
    "Skor_Reserve": reserve_score,
    "Estimasi_Reserve": reserve_volume,
})
reserve_table["Status"] = reserve_table["Skor_Reserve"].apply(lambda x: "Reserve" if x > 0 else "Subeconomic / Resource")

c5, c6 = st.columns(2)
with c5:
    st.dataframe(reserve_table, use_container_width=True)
with c6:
    fig_res, ax_res = plt.subplots()
    ax_res.plot(reserve_table["Tahun"], reserve_table["Skor_Reserve"], marker="o")
    ax_res.set_xlabel("Tahun")
    ax_res.set_ylabel("Skor Kelayakan Reserve")
    st.pyplot(fig_res)

st.write("""
Jika harga naik atau teknologi menekan biaya efektif, sebagian resource bergerak menjadi reserve.
Inilah inti spektrum cadangan: perubahan status ekonomis karena perubahan pasar dan teknologi.
""")

st.download_button(
    "Download Tabel Spektrum Cadangan CSV",
    data=reserve_table.to_csv(index=False).encode("utf-8"),
    file_name="spektrum_cadangan_emas.csv",
    mime="text/csv",
)

# 4.2 Hotelling pure test
st.markdown("### 4.2 Simulasi Hotelling Rule (Model Dasar) - Uji Teori Hotelling Murni")
hotelling_df = data[["Tahun", "Harga_Emas"]].copy()
hotelling_df["Hotelling_Benchmark"] = first_price * ((1 + discount_rate) ** (hotelling_df.index))
hotelling_df["Selisih"] = hotelling_df["Harga_Emas"] - hotelling_df["Hotelling_Benchmark"]
avg_gap = hotelling_df["Selisih"].mean()
avg_actual_growth = avg_price_growth

colh1, colh2 = st.columns(2)
with colh1:
    st.dataframe(hotelling_df, use_container_width=True)
with colh2:
    fig_hot, ax_hot = plt.subplots()
    ax_hot.plot(hotelling_df["Tahun"], hotelling_df["Harga_Emas"], marker="o", label="Harga Aktual")
    ax_hot.plot(hotelling_df["Tahun"], hotelling_df["Hotelling_Benchmark"], marker="o", label="Benchmark Hotelling")
    ax_hot.set_xlabel("Tahun")
    ax_hot.set_ylabel("Harga")
    ax_hot.legend()
    st.pyplot(fig_hot)

st.write(f"""
Rata-rata pertumbuhan harga aktual adalah {avg_actual_growth:.2f}% per tahun, sedangkan tingkat bunga
simulasi adalah {discount_rate*100:.2f}%. Selisih rata-rata aktual terhadap benchmark Hotelling adalah
{fmt_idr(avg_gap)}. Jika selisih kecil, jalur aktual mendekati efisiensi intertemporal; jika selisih
besar, berarti ada distorsi pasar, biaya ekstraksi, atau mekanisme pasar yang menyimpang.
""")

st.download_button(
    "Download Tabel Hotelling CSV",
    data=hotelling_df.to_csv(index=False).encode("utf-8"),
    file_name="hotelling_emas.csv",
    mime="text/csv",
)

# 4.3 Green paradox
st.markdown("### 4.3 Simulasi Green Paradox (Tabel dan Grafik)")
announce_year = st.slider("Tahun pengumuman kebijakan hijau (indeks waktu)", 1, horizon - 1 if horizon > 1 else 1, max(1, horizon // 2), 1)
base_extraction = max((a - mc_value) / b, 0)

gp_rows = []
for t in range(horizon + 1):
    base_q = max(base_extraction * (1 - 0.06 * t), 0)
    if t < announce_year:
        q_policy = base_q * (1 + reg_intensity / 100 * 0.60)
    elif t == announce_year:
        q_policy = base_q * (1 + reg_intensity / 100 * 0.25)
    else:
        q_policy = base_q * (1 - reg_intensity / 100 * 0.20)
    gp_rows.append({
        "Tahun": t,
        "Ekstraksi_Baseline": base_q,
        "Ekstraksi_dengan_Kebijakan": q_policy,
        "Selisih": q_policy - base_q
    })

gp_table = pd.DataFrame(gp_rows)
g1, g2 = st.columns(2)
with g1:
    st.dataframe(gp_table, use_container_width=True)
with g2:
    fig_gp, ax_gp = plt.subplots()
    ax_gp.plot(gp_table["Tahun"], gp_table["Ekstraksi_Baseline"], marker="o", label="Baseline")
    ax_gp.plot(gp_table["Tahun"], gp_table["Ekstraksi_dengan_Kebijakan"], marker="o", label="Dengan Kebijakan")
    ax_gp.set_xlabel("Tahun")
    ax_gp.set_ylabel("Ekstraksi")
    ax_gp.legend()
    st.pyplot(fig_gp)

st.write("""
Ketika kebijakan hijau diumumkan, produsen dapat mempercepat ekstraksi sebelum regulasi berlaku.
Itulah efek Green Paradox: aturan yang dimaksudkan mengendalikan emisi justru memicu percepatan
ekstraksi di awal.
""")
# -----------------------------
# IDENTIFIKASI DISTORSI PASAR
# -----------------------------

st.markdown("#### Identifikasi Distorsi Pasar")

st.write("""
Harga pasar sumber daya alam sering kali belum memasukkan biaya sosial lingkungan seperti kerusakan lahan, pencemaran, dan degradasi lingkungan. Akibatnya, harga pasar menjadi lebih murah dibandingkan
biaya sosial sebenarnya (social cost). Fenomena ini disebut distorsi pasar akibat eksternalitas negatif.
""")

# INPUT BIAYA SOSIAL
social_cost = st.slider(
    "Estimasi biaya sosial lingkungan",
    0.0,
    1500.0,
    400.0,
    10.0
)

# PERHITUNGAN
social_price = mc_value + social_cost
distortion_gap = social_price - mc_value

# TABEL
distortion_df = pd.DataFrame({
    "Komponen": [
        "Marginal Cost (MC)",
        "Biaya Sosial",
        "Total Social Cost"
    ],
    "Nilai": [
        mc_value,
        social_cost,
        social_price
    ]
})

st.dataframe(distortion_df, use_container_width=True)

# GRAFIK
fig_dist, ax_dist = plt.subplots()

kategori = [
    "MC",
    "Biaya Sosial",
    "Social Cost"
]

nilai = [
    mc_value,
    social_cost,
    social_price
]

ax_dist.bar(kategori, nilai)

ax_dist.set_ylabel("Biaya")

st.pyplot(fig_dist)

# INTERPRETASI
st.write(f"""
Simulasi menunjukkan bahwa biaya ekstraksi langsung (MC)
sebesar {fmt_idr(mc_value)} belum mencerminkan
seluruh biaya lingkungan.

Ketika biaya sosial dimasukkan,
total social cost meningkat menjadi
{fmt_idr(social_price)}.

Hal ini menunjukkan adanya distorsi pasar
karena harga pasar belum sepenuhnya
menginternalisasi dampak lingkungan.
""")

st.download_button(
    "Download Tabel Green Paradox CSV",
    data=gp_table.to_csv(index=False).encode("utf-8"),
    file_name="green_paradox_emas.csv",
    mime="text/csv",
)

# -----------------------------
# MEKANISME STRUKTUR PASAR
# -----------------------------
st.markdown("### 4.4 Mekanisme Struktur Pasar dan Evaluasi Hotelling")

st.write("""
Bagian ini mensimulasikan bagaimana jumlah perusahaan memengaruhi harga,
jumlah produksi, market power, dan efisiensi intertemporal sumber daya emas.

Jika:
- jumlah perusahaan = 1 → monopoli
- jumlah perusahaan = 2 → duopoli
- jumlah perusahaan ≥ 3 → oligopoli

Semakin sedikit jumlah perusahaan, semakin besar kekuatan pasar (market power)
dan semakin besar peluang penyimpangan dari efisiensi Hotelling.
""")

# -----------------------------
# INPUT STRUKTUR PASAR
# -----------------------------
jumlah_perusahaan = st.slider(
    "Jumlah perusahaan dalam pasar",
    1,
    10,
    3,
    1
)

# -----------------------------
# PENENTUAN STRUKTUR PASAR
# -----------------------------
if jumlah_perusahaan == 1:
    struktur_pasar = "Monopoli"

elif jumlah_perusahaan == 2:
    struktur_pasar = "Duopoli"

else:
    struktur_pasar = "Oligopoli"

# -----------------------------
# RUMUS COURNOT
# -----------------------------
Q_market = (
    (jumlah_perusahaan * (a - mc_value))
    / (b * (jumlah_perusahaan + 1))
)

P_market = a - (b * Q_market)

markup = P_market - mc_value

produksi_perusahaan = Q_market / jumlah_perusahaan

# -----------------------------
# TABEL HASIL
# -----------------------------
market_result = pd.DataFrame({
    "Struktur Pasar": [struktur_pasar],
    "Jumlah Perusahaan": [jumlah_perusahaan],
    "Harga Pasar": [P_market],
    "Total Produksi": [Q_market],
    "Produksi per Perusahaan": [produksi_perusahaan],
    "Markup terhadap MC": [markup]
})

st.dataframe(market_result, use_container_width=True)

# -----------------------------
# GRAFIK
# -----------------------------
fig_market, ax_market = plt.subplots()

kategori = [
    "Harga",
    "Total Produksi",
    "Markup"
]

nilai = [
    P_market,
    Q_market,
    markup
]

ax_market.bar(kategori, nilai)

ax_market.set_title(
    f"Simulasi Struktur Pasar: {struktur_pasar}"
)

st.pyplot(fig_market)

# -----------------------------
# INTERPRETASI EKONOMI
# -----------------------------
st.write(f"""
Hasil simulasi menunjukkan bahwa struktur pasar saat ini termasuk
**{struktur_pasar}** dengan jumlah perusahaan sebanyak
**{jumlah_perusahaan} perusahaan**.

Harga pasar hasil simulasi sebesar
**{fmt_idr(P_market)}** dengan total produksi sebesar
**{fmt_num(Q_market)}**.

Nilai markup terhadap marginal cost sebesar
**{fmt_idr(markup)}** menunjukkan adanya market power
dalam pembentukan harga.

Semakin sedikit jumlah perusahaan, maka:
- harga cenderung lebih tinggi,
- produksi cenderung lebih rendah,
- dan penyimpangan dari efisiensi Hotelling semakin besar.

Sebaliknya, ketika jumlah perusahaan meningkat,
struktur pasar bergerak mendekati persaingan sempurna,
sehingga harga semakin dekat dengan biaya ekstraksi.
""")

# -----------------------------
# EVALUASI HOTELLING
# -----------------------------
st.markdown("#### Evaluasi Efisiensi Hotelling")

if markup > 500:
    evaluasi_hotelling = """
    Struktur pasar menunjukkan market power yang cukup kuat.
    Harga jauh di atas biaya ekstraksi sehingga jalur harga
    berpotensi menyimpang dari efisiensi Hotelling.
    """

elif markup > 100:
    evaluasi_hotelling = """
    Struktur pasar menunjukkan market power sedang.
    Jalur harga masih mengandung deviasi terhadap kondisi efisiensi.
    """

else:
    evaluasi_hotelling = """
    Struktur pasar relatif mendekati persaingan sempurna.
    Harga semakin dekat dengan biaya ekstraksi sehingga
    lebih mendekati kondisi efisiensi Hotelling.
    """

st.info(evaluasi_hotelling)

# -----------------------------
# DOWNLOAD CSV
# -----------------------------
st.download_button(
    "Download Struktur Pasar CSV",
    data=market_result.to_csv(index=False).encode("utf-8"),
    file_name="simulasi_struktur_pasar.csv",
    mime="text/csv",
)

# -----------------------------
# JAWABAN RUMUSAN MASALAH
# -----------------------------
st.markdown("### 4.5 Jawaban Rumusan Masalah")

st.write("""
1. Perubahan harga dan teknologi memengaruhi pergeseran resource ke reserve karena kelayakan ekonomis berubah.
2. Jalur ekstraksi yang efisien harus mengikuti logika Hotelling, yaitu harga bersih meningkat seiring waktu.
3. Green Paradox muncul ketika kebijakan hijau memicu percepatan ekstraksi sebelum regulasi diberlakukan.
4. Struktur pasar memengaruhi besar kecilnya markup, sehingga ikut menentukan penyimpangan dari efisiensi intertemporal.
""")

# -----------------------------
# BAB V
# -----------------------------
st.subheader("BAB V. Kesimpulan dan Rekomendasi")

st.markdown("### 5.1 Kesimpulan")
st.write("""
Harga emas menunjukkan tren meningkat, sementara stock emas terus mengalami penurunan. Fenomena ini
menunjukkan tekanan kelangkaan pada sumber daya depletable. Analisis ini menegaskan relevansi
Hotelling Rule, efisiensi dinamis, green paradox, dan pergeseran resource menjadi reserve dalam
pengelolaan sumber daya alam modern.
""")

st.markdown("### 5.2 Rekomendasi / Kebijakan Solutif")
st.write("""
Pemerintah perlu mengatur tempo ekstraksi, memperkuat insentif teknologi hemat biaya, mendorong
substitusi, dan merancang kebijakan lingkungan yang bertahap agar tidak memicu race to extract
atau Green Paradox. Instrumen pasar dan pengawasan harus dirancang agar efisien sekaligus adil
lintas generasi.
""")

st.divider()
st.caption("Dikembangkan untuk PBL 3 - Ekonomi SDA & Lingkungan | Analisis Intertemporal Sumber Daya Emas")
