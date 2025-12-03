import pika
import json
import time

# Konfigurasi Koneksi
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Deklarasi Exchange (Pintu Masuk)
channel.exchange_declare(exchange='booking_exchange', exchange_type='direct')

def load_scenarios():
    with open('scenarios.json', 'r') as f:
        return json.load(f)

def run_producer():
    scenarios = load_scenarios()
    print("--- [GATEWAY] Simulator Started ---")

    for action in scenarios:
        event_type = action['action']
        payload = action['data']
        message = json.dumps(payload)

        if event_type == "MAKE_PAYMENT":
            # E1: Booking Submitted -> Kirim ke Booking Service
            routing_key = "booking.submit"
            print(f" [x] Passenger initiates Payment for {payload['bookingId']}")
            channel.basic_publish(exchange='booking_exchange', routing_key=routing_key, body=message)
        
        elif event_type == "CANCEL_TICKET":
            # Initiating Cancellation -> Kirim ke Booking Service
            routing_key = "booking.cancel_request"
            print(f" [x] Passenger initiates Cancellation for {payload['bookingId']}")
            channel.basic_publish(exchange='booking_exchange', routing_key=routing_key, body=message)

        time.sleep(2) # Jeda biar enak dilihat di terminal lain

    connection.close()

if __name__ == "__main__":
    run_producer()
