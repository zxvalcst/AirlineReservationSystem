import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Hanya perlu mendengarkan Status Exchange (Fanout)
channel.exchange_declare(exchange='status_exchange', exchange_type='fanout')

queue_name = channel.queue_declare(queue='', exclusive=True).method.queue
channel.queue_bind(exchange='status_exchange', queue=queue_name)

def callback(ch, method, properties, body):
    data = json.loads(body)
    status = data['status']
    booking_id = data['bookingId']

    print(f" [Notification] Menerima event update untuk {booking_id} -> {status}")

    if status == "Confirmed":
        print(f"   >>> 📧 EMAIL: E-TICKET Terkirim & SMS Sukses ke user untuk {booking_id}")
    
    elif status == "Payment Failed":
        print(f"   >>> ⚠️ ALERT: Pembayaran GAGAL untuk {booking_id}. Saldo tidak cukup/ditolak Bank.")
    
    elif status == "Refunded":
        print(f"   >>> 📧 EMAIL: Konfirmasi Refund berhasil untuk {booking_id}")

    # --- TAMBAHAN BARU UNTUK VALIDASI ---
    elif status == "Validation Failed":
        reason = data.get('reason', 'Data tidak valid')
        print(f"   >>> ❌ ERROR: Booking Ditolak Sistem! ID: {booking_id}")
        print(f"       Pesan ke User: 'Mohon maaf, {reason}. Silakan ulangi pemesanan.'")

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue=queue_name, on_message_callback=callback)
print(' [*] Notification Service Waiting for events...')
channel.start_consuming()
