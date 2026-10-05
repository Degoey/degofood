"""Service notifikasi WhatsApp untuk DEGOFOOD.

Pada tahap MVP ini notifikasi hanya disimulasikan dengan mencetak log ke
terminal backend, sehingga alur integrasi bisa diuji tanpa biaya API pihak
ketiga (mis. WhatsApp Cloud API / Twilio / Fonnte).

Untuk produksi, cukup ganti isi fungsi `send_whatsapp_message` dengan
pemanggilan HTTP ke provider WhatsApp yang dipilih.
"""


def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """Kirim (simulasi) pesan WhatsApp ke `phone_number`.

    Args:
        phone_number: Nomor telepon tujuan, mis. '081234567890'.
        message: Isi pesan yang akan dikirim.

    Returns:
        True jika pesan berhasil "dikirim" (pada simulasi selalu True).
    """
    print(f"\n[WHATSAPP SIMULATION] Mengirim ke {phone_number}: {message}\n")
    return True
