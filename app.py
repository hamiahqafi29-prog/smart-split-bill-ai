import json
import os
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from smart_split.ai import ExtractionError, extract_receipt
from smart_split.models import empty_receipt, normalize_receipt
from smart_split.splitter import calculate_split, format_idr


load_dotenv()

CREATOR_NAME = "Hami Ahqafi"

st.set_page_config(
    page_title="Smart Split Bill AI",
    page_icon="🧾",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem;}
    [data-testid="stMetric"] {
        background: #f7f8fa;
        border: 1px solid #e8eaed;
        border-radius: 14px;
        padding: 14px;
    }
    .receipt-card {
        border: 1px solid #e8eaed;
        border-radius: 16px;
        padding: 18px;
        background: white;
        margin-bottom: 12px;
    }
    .muted {color: #687076; font-size: .92rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    defaults = {
        "receipt": empty_receipt(),
        "participants": ["Aku"],
        "assignments": {},
        "extracted": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def sync_receipt(items_df: pd.DataFrame, charges_df: pd.DataFrame, subtotal, total) -> None:
    items = []
    for row in items_df.fillna("").to_dict("records"):
        qty = to_decimal(row.get("Jumlah"))
        unit_price = to_decimal(row.get("Harga/item"))
        line_total = to_decimal(row.get("Total item"))
        if not line_total and qty and unit_price:
            line_total = qty * unit_price
        if row.get("Nama item"):
            items.append(
                {
                    "name": str(row["Nama item"]).strip(),
                    "quantity": float(qty),
                    "unit_price": float(unit_price),
                    "total": float(line_total),
                }
            )

    charges = []
    for row in charges_df.fillna("").to_dict("records"):
        if row.get("Biaya tambahan"):
            charges.append(
                {
                    "name": str(row["Biaya tambahan"]).strip(),
                    "amount": float(to_decimal(row.get("Nominal"))),
                }
            )

    st.session_state.receipt = normalize_receipt(
        {
            "merchant": st.session_state.receipt.get("merchant", ""),
            "items": items,
            "subtotal": float(to_decimal(subtotal)),
            "charges": charges,
            "total": float(to_decimal(total)),
        }
    )


init_state()

st.title("🧾 Smart Split Bill AI")
st.caption(
    "Upload nota, periksa hasil pembacaan AI, lalu tentukan siapa menikmati item apa."
)
st.markdown(
    f"<p class='muted'>Created by: <strong>{CREATOR_NAME}</strong></p>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("1. Baca nota")
    uploaded_file = st.file_uploader(
        "Upload gambar nota",
        type=["jpg", "jpeg", "png", "webp"],
        help="Gunakan gambar yang terang, fokus, dan seluruh nota terlihat.",
    )

    provider = st.selectbox(
        "AI provider",
        ["Hugging Face", "Groq Vision", "OpenAI", "Demo / input manual"],
        help=(
            "Hugging Face membutuhkan HF_TOKEN dengan izin Inference Providers. "
            "Groq membutuhkan GROQ_API_KEY. OpenAI membutuhkan quota API aktif."
        ),
    )
    default_models = {
        "Hugging Face": "Qwen/Qwen3-VL-8B-Instruct:fastest",
        "Groq Vision": "meta-llama/llama-4-scout-17b-16e-instruct",
        "OpenAI": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "Demo / input manual": "",
    }
    model = st.text_input(
        "Model vision",
        value=default_models[provider],
        disabled=provider == "Demo / input manual",
        key=f"model_{provider}",
    )

    if uploaded_file:
        st.image(uploaded_file, caption="Nota yang diupload", width="stretch")

    extract_clicked = st.button(
        "✨ Ekstrak data nota",
        type="primary",
        width="stretch",
        disabled=uploaded_file is None or provider == "Demo / input manual",
    )

    if extract_clicked and uploaded_file:
        try:
            with st.spinner("AI sedang membaca nota..."):
                result = extract_receipt(
                    uploaded_file.getvalue(),
                    uploaded_file.type,
                    provider={
                        "Hugging Face": "huggingface",
                        "Groq Vision": "groq",
                        "OpenAI": "openai",
                    }[provider],
                    model=model,
                )
            st.session_state.receipt = normalize_receipt(result)
            st.session_state.assignments = {}
            st.session_state.extracted = True
            st.success("Nota berhasil dibaca. Silakan periksa hasilnya.")
            st.rerun()
        except ExtractionError as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("**Mode demo**")
    if st.button("Muat contoh transaksi", width="stretch"):
        st.session_state.receipt = normalize_receipt(
            {
                "merchant": "Kopi Bersama",
                "items": [
                    {"name": "Nasi Goreng", "quantity": 2, "unit_price": 28000, "total": 56000},
                    {"name": "Es Teh", "quantity": 3, "unit_price": 8000, "total": 24000},
                    {"name": "Kentang Goreng", "quantity": 1, "unit_price": 22000, "total": 22000},
                ],
                "subtotal": 102000,
                "charges": [
                    {"name": "Service 5%", "amount": 5100},
                    {"name": "Pajak", "amount": 10710},
                ],
                "total": 117810,
            }
        )
        st.session_state.assignments = {}
        st.session_state.extracted = True
        st.rerun()

receipt = st.session_state.receipt

st.subheader("2. Periksa data transaksi")
st.caption("Hasil AI tetap dapat diedit. Koreksi data sebelum melakukan pembagian.")

merchant = st.text_input("Nama merchant", value=receipt.get("merchant", ""))
st.session_state.receipt["merchant"] = merchant

items_df = pd.DataFrame(
    [
        {
            "Nama item": item["name"],
            "Jumlah": item["quantity"],
            "Harga/item": item["unit_price"],
            "Total item": item["total"],
        }
        for item in receipt["items"]
    ],
    columns=["Nama item", "Jumlah", "Harga/item", "Total item"],
)

edited_items = st.data_editor(
    items_df,
    num_rows="dynamic",
    width="stretch",
    hide_index=True,
    column_config={
        "Nama item": st.column_config.TextColumn(required=True),
        "Jumlah": st.column_config.NumberColumn(min_value=0.0, step=1.0),
        "Harga/item": st.column_config.NumberColumn(min_value=0.0, format="Rp %.0f"),
        "Total item": st.column_config.NumberColumn(min_value=0.0, format="Rp %.0f"),
    },
    key="items_editor",
)

charges_df = pd.DataFrame(
    [
        {"Biaya tambahan": charge["name"], "Nominal": charge["amount"]}
        for charge in receipt["charges"]
    ],
    columns=["Biaya tambahan", "Nominal"],
)

left, right = st.columns([1.5, 1])
with left:
    st.markdown("**Pajak, service, dan biaya tambahan**")
    edited_charges = st.data_editor(
        charges_df,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "Biaya tambahan": st.column_config.TextColumn(required=True),
            "Nominal": st.column_config.NumberColumn(format="Rp %.0f"),
        },
        key="charges_editor",
    )

with right:
    calculated_subtotal = float(
        sum(to_decimal(row.get("Total item")) for row in edited_items.to_dict("records"))
    )
    subtotal = st.number_input(
        "Subtotal pada nota",
        min_value=0.0,
        value=float(receipt.get("subtotal") or calculated_subtotal),
        step=1000.0,
        format="%.0f",
    )
    total = st.number_input(
        "Total bill",
        min_value=0.0,
        value=float(receipt.get("total") or subtotal),
        step=1000.0,
        format="%.0f",
    )

sync_receipt(edited_items, edited_charges, subtotal, total)
receipt = st.session_state.receipt

st.divider()
st.subheader("3. Tambahkan orang dan pilih item")

participant_text = st.text_input(
    "Nama peserta (pisahkan dengan koma)",
    value=", ".join(st.session_state.participants),
    placeholder="Aku, Budi, Siti",
)
participants = list(
    dict.fromkeys(name.strip() for name in participant_text.split(",") if name.strip())
)
st.session_state.participants = participants

if not participants:
    st.warning("Tambahkan minimal satu nama peserta.")
else:
    st.caption("Satu item dapat dipilih oleh beberapa orang dan akan dibagi sama rata.")
    assignments = {}
    for index, item in enumerate(receipt["items"]):
        key = f"item_{index}"
        previous = [
            name
            for name in st.session_state.assignments.get(key, participants[:1])
            if name in participants
        ]
        cols = st.columns([2.4, 1, 2.6])
        with cols[0]:
            st.markdown(f"**{item['name']}**")
            st.caption(
                f"{item['quantity']:g} × {format_idr(item['unit_price'])}"
            )
        with cols[1]:
            st.markdown(f"**{format_idr(item['total'])}**")
        with cols[2]:
            assignments[key] = st.multiselect(
                "Dibayar oleh",
                participants,
                default=previous,
                key=f"assign_{index}_{'|'.join(participants)}",
                label_visibility="collapsed",
                placeholder="Pilih nama",
            )
    st.session_state.assignments = assignments

    unassigned = [
        receipt["items"][i]["name"]
        for i in range(len(receipt["items"]))
        if not assignments.get(f"item_{i}")
    ]

    st.divider()
    st.subheader("4. Hasil split bill")
    st.caption(f"Split bill dibuat oleh: {CREATOR_NAME}")

    if unassigned:
        st.warning("Belum ada pembayar untuk: " + ", ".join(unassigned))
    elif not receipt["items"]:
        st.info("Tambahkan item transaksi terlebih dahulu.")
    else:
        split = calculate_split(receipt, participants, assignments)
        summary_cols = st.columns(min(len(participants), 4))
        for index, person in enumerate(participants):
            with summary_cols[index % len(summary_cols)]:
                st.metric(person, format_idr(split["people"][person]["total"]))

        with st.expander("Lihat rincian per orang", expanded=True):
            for person in participants:
                details = split["people"][person]
                st.markdown(f"#### {person} · {format_idr(details['total'])}")
                rows = [
                    {"Keterangan": row["label"], "Nominal": format_idr(row["amount"])}
                    for row in details["lines"]
                    if row["amount"]
                ]
                st.dataframe(rows, width="stretch", hide_index=True)

        check_left, check_right, check_status = st.columns(3)
        with check_left:
            st.metric("Total seluruh orang", format_idr(split["allocated_total"]))
        with check_right:
            st.metric("Total bill", format_idr(split["bill_total"]))
        with check_status:
            difference = split["bill_total"] - split["allocated_total"]
            st.metric("Selisih", format_idr(difference))

        if split["is_balanced"]:
            st.success("✅ Pembagian seimbang: total semua orang sama persis dengan total bill.")
        else:
            st.error("Pembagian belum seimbang. Periksa total transaksi.")

        st.download_button(
            "Download hasil (JSON)",
            data=json.dumps(
                {"created_by": CREATOR_NAME, **split},
                indent=2,
                ensure_ascii=False,
            ),
            file_name="hasil_split_bill.json",
            mime="application/json",
        )
