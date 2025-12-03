import pika
import json
import os

# Setup Database Sederhana
DB_FILE = 'database.json'

def update_db(booking_id, status):
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try: data = json.load(f)
            except: data = []
    
    # Cek if exist update, else create
    found = False
    for item in data:
        if item['bookingId'] == booking_id:
            item['status'] = status
            found = True
            break
    if not found:
        data.append({"bookingId": booking_id, "status": status})
    
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print(f" [DB] Database updated: {booking_id} -> {status}")

# Koneksi RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declare Exchanges
channel.exchange_declare(exchange='booking_exchange', exchange_type='direct') # Input dari UI
channel.exchange_declare(exchange='payment_exchange', exchange_type='direct') # Kirim ke Payment
channel.exchange_declare(exchange='status_exchange', exchange_type='fanout') # Terima status (Fanout)

# Queue untuk menerima Request dari UI
q_booking = channel.queue_declare(queue='', exclusive=True).method.queue
channel.queue_bind(exchange='booking_exchange', queue=q_booking, routing_key='booking.submit')
channel.queue_bind(exchange='booking_exchange', queue=q_booking, routing_key='booking.cancel_request')

# Queue untuk menerima Status Update (Fanout dari Payment)
q_status = channel.queue_declare(queue='', exclusive=True).method.queue
channel.queue_bind(exchange='status_exchange', queue=q_status)

def callback(ch, method, properties, body):
    data = json.loads(body)
    routing_key = method.routing_key
    
    # 1. Menangani Booking Baru
    if routing_key == "booking.submit":
        print(f" [BookingService] Menerima pesanan baru: {data['bookingId']}")
        # Validasi sederhana
        if data['amount'] > 0:
            print("   -> Validasi Internal OK. Meneruskan ke PaymentService...")
            update_db(data['bookingId'], "Pending Payment")
            
            # E1 Output: Kirim ke Payment Service
            channel.basic_publish(exchange='payment_exchange', routing_key='payment.process', body=body)
        else:
            print("   -> Validasi Gagal: Amount invalid.")

    # 2. Menangani Request Cancel (Simulasi Admin Approval disini)
    elif routing_key == "booking.cancel_request":
        print(f" [BookingService] Menerima request cancel: {data['bookingId']}")
        # Simulasi Admin Approval (Langsung dianggap Approved)
        print("   -> (AdminService Mock) Admin menyetujui pembatalan.")
        
        # E4: Cancellation Approved -> Kirim ke Payment Service untuk Refund
        channel.basic_publish(exchange='payment_exchange', routing_key='payment.refund', body=body)

    # 3. Menangani Update Status (Dari Payment Service)
    elif "status" in data: 
        new_status = data['status']
        print(f" [BookingService] Menerima update status: {new_status} untuk {data['bookingId']}")
        update_db(data['bookingId'], new_status)

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue=q_booking, on_message_callback=callback)
channel.basic_consume(queue=q_status, on_message_callback=callback)

print(' [*] Booking Service Waiting for messages...')
channel.start_consuming()
