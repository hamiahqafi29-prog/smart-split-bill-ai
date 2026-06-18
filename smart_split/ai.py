import base64
import json
import os

from openai import OpenAI


class ExtractionError(RuntimeError):
    pass


SYSTEM_PROMPT = """
Anda adalah mesin ekstraksi data nota Indonesia. Baca gambar dengan teliti dan
kembalikan hanya JSON valid, tanpa markdown. Jangan mengarang nilai yang tidak
terlihat. Semua nominal harus berupa angka tanpa simbol mata uang atau pemisah
ribuan.

Struktur JSON:
{
  "merchant": "nama toko/restoran",
  "items": [
    {
      "name": "nama item",
      "quantity": 1,
      "unit_price": 10000,
      "total": 10000
    }
  ],
  "subtotal": 10000,
  "charges": [
    {"name": "Pajak", "amount": 1000}
  ],
  "total": 11000
}

Aturan:
- Pisahkan pajak, service charge, delivery fee, rounding, discount, dan biaya
  lain sebagai charges. Diskon bernilai negatif.
- quantity adalah angka dan boleh desimal.
- Pastikan quantity × unit_price masuk akal terhadap total item.
- Jika subtotal tercetak, gunakan nilai yang tercetak.
- Total bill adalah nilai berlabel TOTAL, GRAND TOTAL, atau TOTAL BILL.
- Jangan gunakan CASH, TUNAI, PAID AMOUNT, TENDERED, jumlah uang diterima,
  atau uang kembalian sebagai total bill.
- Periksa konsistensi: total bill seharusnya sama dengan subtotal ditambah
  charges (termasuk diskon negatif), selain jika nota memperlihatkan rounding.
- Jika suatu field tidak terbaca, gunakan 0 atau string kosong.
"""


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            "AI tidak mengembalikan data JSON yang valid. Coba gambar lain atau koreksi manual."
        ) from exc
    if not isinstance(data, dict):
        raise ExtractionError("Format hasil AI tidak sesuai.")
    return data


def extract_receipt(
    image_bytes: bytes,
    mime_type: str,
    provider: str = "openai",
    model: str = "gpt-4.1-mini",
) -> dict:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ExtractionError(
                "OPENAI_API_KEY belum ditemukan. Tambahkan ke file .env atau gunakan mode demo."
            )
        client = OpenAI(api_key=api_key)
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": SYSTEM_PROMPT},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
            )
            return _parse_json(response.output_text)
        except Exception as exc:
            message = str(exc)
            if "insufficient_quota" in message or "exceeded your current quota" in message:
                raise ExtractionError(
                    "Quota OpenAI API habis atau billing belum aktif. Aktifkan billing "
                    "OpenAI, atau pilih Groq Vision."
                ) from exc
            raise ExtractionError(f"Gagal memanggil OpenAI: {exc}") from exc

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ExtractionError(
                "GROQ_API_KEY belum ditemukan. Buat key di console.groq.com/keys "
                "lalu tambahkan ke file .env."
            )
        if len(image_bytes) > 4 * 1024 * 1024:
            raise ExtractionError(
                "Gambar lebih dari 4 MB. Kompres gambar terlebih dahulu untuk Groq Vision."
            )
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            return _parse_json(response.choices[0].message.content or "")
        except Exception as exc:
            raise ExtractionError(f"Gagal memanggil Groq Vision: {exc}") from exc

    if provider == "huggingface":
        api_key = os.getenv("HF_TOKEN")
        if not api_key:
            raise ExtractionError(
                "HF_TOKEN belum ditemukan. Buat fine-grained token dengan izin "
                "'Make calls to Inference Providers', lalu tambahkan ke file .env."
            )
        client = OpenAI(
            api_key=api_key,
            base_url="https://router.huggingface.co/v1",
        )
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SYSTEM_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    }
                ],
                temperature=0,
                max_tokens=2048,
            )
            return _parse_json(response.choices[0].message.content or "")
        except Exception as exc:
            message = str(exc)
            if "permission" in message.lower() or "403" in message:
                raise ExtractionError(
                    "HF_TOKEN tidak memiliki izin Inference Providers. Buat fine-grained "
                    "token dan aktifkan 'Make calls to Inference Providers'."
                ) from exc
            raise ExtractionError(f"Gagal memanggil Hugging Face: {exc}") from exc

    raise ExtractionError(f"Provider belum didukung: {provider}")
