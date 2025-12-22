import pika
import json
import os

# Setup Database Sederhana
DB_FILE = 'database.json'

# --- FUNGSI BARU: CEK EKSISTENSI DATA ---
def check_booking_exists(booking_id):
    if not os.path.exists(DB_FILE):
        return False
    
    with open(DB_FILE, 'r') as f:
        try: 
            data = json.load(f)
            for item in data:
                if item['bookingId'] == booking_id:
                    return True
        except: 
            return False
    return False

def update_db(booking_id, status):
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try: data = json.load(f)
            except: data = []
    
    found = False
    for item in data:
        if item['bookingId'] == booking_id:
            item['status'] = status
            found = True
            break
    
    # KITA UBAH SEDIKIT: Hanya create baru jika statusnya bukan Refunded
    # Atau biarkan seperti ini, karena kita sudah cegah di logic utama.
    if not found:
        data.append({"bookingId": booking_id, "status": status})
    
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print(f" [DB] Database updated: {booking_id} -> {status}")

# Koneksi RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declare Exchanges
channel.exchange_declare(exchange='booking_exchange', exchange_type='direct')
channel.exchange_declare(exchange='payment_exchange', exchange_type='direct')
channel.exchange_declare(exchange='status_exchange', exchange_type='fanout')

# Queues
q_booking = channel.queue_declare(queue='', exclusive=True).method.queue
channel.queue_bind(exchange='booking_exchange', queue=q_booking, routing_key='booking.submit')
channel.queue_bind(exchange='booking_exchange', queue=q_booking, routing_key='booking.cancel_request')

q_status = channel.queue_declare(queue='', exclusive=True).method.queue
channel.queue_bind(exchange='status_exchange', queue=q_status)

def callback(ch, method, properties, body):
    data = json.loads(body)
    routing_key = method.routing_key
    
    # 1. Menangani Booking Baru
    if routing_key == "booking.submit":
        print(f" [BookingService] Menerima pesanan baru: {data['bookingId']}")
        if data['amount'] > 0:
            print("   -> Validasi Internal OK. Meneruskan ke PaymentService...")
            update_db(data['bookingId'], "Pending Payment")
            channel.basic_publish(exchange='payment_exchange', routing_key='payment.process', body=body)
        else:
            print("   -> Validasi Gagal: Amount invalid.")
            # Jangan update DB jika invalid, atau update sebagai 'Failed'
            
            failure_data = {
                "bookingId": data['bookingId'],
                "status": "Validation Failed",
                "reason": "Jumlah pembayaran tidak valid (0 atau negatif)"
            }
            channel.basic_publish(exchange='status_exchange', routing_key='', body=json.dumps(failure_data))

    # 2. Menangani Request Cancel
    elif routing_key == "booking.cancel_request":
        print(f" [BookingService] Menerima request cancel: {data['bookingId']}")
        
        # --- PERBAIKAN VALIDASI DATABASE DI SINI ---
        if check_booking_exists(data['bookingId']):
            print("   -> Data ditemukan. (AdminService Mock) Admin menyetujui pembatalan.")
            channel.basic_publish(exchange='payment_exchange', routing_key='payment.refund', body=body)
        else:
            print("   -> ❌ GAGAL: Booking ID tidak ditemukan di Database!")
            
            # Kirim notifikasi error ke User
            error_data = {
                "bookingId": data['bookingId'],
                "status": "Validation Failed",
                "reason": "Booking ID tidak ditemukan. Tidak bisa memproses Refund."
            }
            channel.basic_publish(exchange='status_exchange', routing_key='', body=json.dumps(error_data))

    # 3. Menangani Update Status
    elif "status" in data: 
        new_status = data['status']
        print(f" [BookingService] Menerima update status: {new_status} untuk {data['bookingId']}")
        update_db(data['bookingId'], new_status)

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue=q_booking, on_message_callback=callback)
channel.basic_consume(queue=q_status, on_message_callback=callback)

print(' [*] Booking Service Waiting for messages...')
channel.start_consuming()