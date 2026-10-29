"""Dashboard Streamlit (4 halaman): Ringkasan, Akurasi Ekstraksi, Kepatuhan Spec, Margin dan Dampak.
Jalankan dari folder project/:  streamlit run code/3-presentation/streamlit/app.py
Membaca CSV yang sudah di-commit di results/ (tidak perlu database atau PDF). Semua data adalah simulasi buatan sendiri."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results"
BLUE, ORANGE, GREY, GREEN = "#1A73E8", "#E8710A", "#9AA0A6", "#188038"
st.set_page_config(page_title="Project 26: Spec Compliance Extraction", layout="wide")
R = lambda d, f: pd.read_csv(RES / d / f)


@st.cache_data
def load():
    return dict(rows=R("3-presentation", "dash_rows.csv"), units=R("3-presentation", "dash_units.csv"), acc=R("1-data-preparation", "extraction_accuracy.csv"),
                err=R("1-data-preparation", "extraction_errors.csv"), docs=R("1-data-preparation", "extraction_doc_eval.csv"), rq=R("1-data-preparation", "review_queue.csv"),
                wil=R("2-analysis", "wilson_passrate.csv"), mdist=R("2-analysis", "margin_distribution.csv"), mpm=R("2-analysis", "margin_param_model.csv"),
                stale=R("2-analysis", "impact_stale_spec.csv"), chi=R("2-analysis", "chi2_models.csv"), pareto=R("2-analysis", "pareto_fail.csv"))


D = load()
page = st.sidebar.radio("Halaman", ["1. Ringkasan", "2. Akurasi Ekstraksi", "3. Kepatuhan Spec", "4. Margin dan Dampak"])
models = st.sidebar.multiselect("Model lampu", ["5W", "9W", "12W"], default=["5W", "9W", "12W"])
st.sidebar.caption("Data simulasi buatan sendiri. Angka dampak berlabel estimated.")
if not models:
    st.warning("Pilih minimal satu model."); st.stop()
rows = D["rows"][D["rows"].model.isin(models)]
units = D["units"][D["units"].model.isin(models)]
st.title("Project 26: Spec Compliance Extraction")
st.caption("Spec dibaca dari PDF datasheet lalu dicocokkan dengan hasil ukur produksi. Data simulasi Mar–Agu 2026; putusan lolos atau gagal dihitung dengan aturan pasti, bukan oleh LLM.")

if page.startswith("1"):
    acc = D["acc"]; a = acc[(acc.scope == "Semua field")].set_index("method").accuracy
    c = st.columns(4)
    c[0].metric("Akurasi ekstraksi (aturan lengkap)", f"{a['rule_full']:.1%}", f"{a['rule_full'] - a['rule_basic']:+.1%} dari aturan dasar".replace(".", ","))
    c[1].metric("Unit lolos semua parameter", f"{units.n_pass.sum() / units.n.sum():.2%}")
    c[2].metric("Hasil ukur dinilai", f"{rows.n.sum():,}".replace(",", "."))
    c[3].metric("Dokumen perlu review manual", f"{len(D['rq'])} dari {D['docs'].doc.nunique()}")
    m = units.groupby("month")[["n", "n_pass"]].sum().reset_index(); m["rate"] = m.n_pass / m.n
    f = go.Figure(go.Bar(x=m.month, y=m.rate, marker_color=BLUE, text=(m.rate * 100).round(2).astype(str) + "%", textposition="outside"))
    f.update_layout(title="Pass rate unit per bulan", yaxis_tickformat=".1%", yaxis_range=[min(m.rate) - 0.01, 1], height=380, margin=dict(t=50))
    st.plotly_chart(f, width="stretch")
    st.info("Pass rate unit = semua parameter yang diukur pada unit itu lolos terhadap revisi spec yang berlaku pada tanggal uji.")
elif page.startswith("2"):
    acc = D["acc"]
    st.subheader("Aturan dasar vs aturan lengkap (gold set 160 field)")
    fm = acc[acc.scope == "Format dokumen"].pivot(index="group", columns="method", values="accuracy")[["rule_basic", "rule_full"]]
    f = go.Figure([go.Bar(name="Aturan dasar", x=fm.index, y=fm.rule_basic, marker_color=GREY), go.Bar(name="Aturan lengkap", x=fm.index, y=fm.rule_full, marker_color=BLUE)])
    f.update_layout(barmode="group", yaxis_tickformat=".0%", title="Akurasi per format dokumen", height=380, margin=dict(t=50))
    st.plotly_chart(f, width="stretch")
    e = D["err"][D["err"].method == "rule_basic"]
    st.subheader("Pareto kesalahan aturan dasar")
    st.dataframe(e.rename(columns={"error_type": "jenis kesalahan", "n": "jumlah", "share": "porsi", "cum_share": "kumulatif"}), hide_index=True)
    st.subheader("Antrean review manual")
    st.dataframe(D["rq"], hide_index=True)
    st.caption("Langkah LLM (Claude API) disediakan di kode tetapi belum dijalankan pada data ini; aturan lengkap dipakai sebagai pembanding.")
elif page.startswith("3"):
    w = D["wil"][D["wil"].model.isin(models)]
    p = w.groupby("parameter")[["n", "n_pass"]].sum().reset_index(); p["rate"] = p.n_pass / p.n
    f = go.Figure(go.Bar(x=p.parameter, y=p.rate, marker_color=BLUE, text=(p.rate * 100).round(2).astype(str) + "%", textposition="outside"))
    f.update_layout(title="Pass rate per parameter", yaxis_tickformat=".1%", yaxis_range=[0.97, 1.002], height=380, margin=dict(t=50))
    st.plotly_chart(f, width="stretch")
    t = w[["parameter", "model", "n", "n_pass", "pass_rate", "ci_low", "ci_high"]].copy()
    for c in ("pass_rate", "ci_low", "ci_high"):
        t[c] = (t[c] * 100).round(2)
    st.subheader("Pass rate dan interval kepercayaan 95% (Wilson), persen")
    st.dataframe(t, hide_index=True)
    st.subheader("Apakah model berbeda? (chi-square per parameter, koreksi Holm)")
    st.dataframe(D["chi"][["parameter", "chi2", "p_value", "p_holm", "cramers_v", "significant_holm_0_05"]].round(4), hide_index=True)
else:
    st.subheader("Hampir gagal: lolos tetapi dekat batas")
    thr = st.slider("Ambang jarak ke batas (simpangan baku)", 0.5, 3.0, 1.0, 0.5)
    md = D["mdist"][D["mdist"].model.isin(models) & (D["mdist"].margin_bin_sd >= 0)]
    near = md[md.margin_bin_sd < thr].groupby("parameter").n.sum()
    tot = rows.groupby("parameter").n.sum()
    share = (near / tot).fillna(0).sort_values(ascending=False)
    f = go.Figure(go.Bar(x=share.index, y=share.values, marker_color=ORANGE))
    f.update_layout(yaxis_tickformat=".1%", title=f"Porsi hasil lolos dengan margin < {thr:.1f} simpangan baku", height=360, margin=dict(t=50))
    st.plotly_chart(f, width="stretch")
    st.subheader("Risiko spec usang (proxy)")
    s = D["stale"].set_index("stale_revision")
    rev = st.selectbox("Revisi lama yang keliru dipakai", list(s.index))
    st.metric("Unit gagal yang tampak lolos", f"{int(s.loc[rev, 'units_fail_hidden'])} dari {int(s.loc[rev, 'units_truly_fail'])}", f"{s.loc[rev, 'share_fail_hidden_units']:.1%} tersembunyi", delta_color="inverse")
    st.subheader("Kalkulator waktu pengecekan manual (estimated)")
    a, b = st.columns(2)
    mins = a.slider("Menit per dokumen (asumsi)", 5, 60, 20, 5); docs = b.number_input("Dokumen spec per tahun", 1, 500, 48)
    st.metric("Jam per tahun yang bisa dihemat", f"{docs * mins / 60:.0f} jam")
    st.caption("Estimated / simulated. Menit per dokumen adalah asumsi, bukan hasil pengukuran.")
