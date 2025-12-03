import pika
import json
import time

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Declare Exchanges
channel.exchange_declare(exchange='payment_exchange', exchange_type='direct') # Input
channel.exchange_declare(exchange='status_exchange', exchange_type='fanout') # Output (Broadcast)

# Queue
queue_name = channel.queue_declare(queue='', exclusive=True).method.queue
channel.queue_bind(exchange='payment_exchange', queue=queue_name, routing_key='payment.process')
channel.queue_bind(exchange='payment_exchange', queue=queue_name, routing_key='payment.refund')

def callback(ch, method, properties, body):
    data = json.loads(body)
    routing_key = method.routing_key

    if routing_key == 'payment.process':
        print(f" [PaymentService] Memproses pembayaran untuk {data['bookingId']}...")
        time.sleep(1) # Simulasi Bank delay
        
        # Simulasi Bank Logic (Sukses jika amount < 2juta, contoh saja)
        if data['amount'] < 2000000:
            status = "Confirmed" # E2: Payment Successful
            print("   -> Bank: Payment Approved.")
        else:
            status = "Payment Failed" # E3: Payment Failed
            print("   -> Bank: Payment Denied (Limit Exceeded).")

    elif routing_key == 'payment.refund':
        print(f" [PaymentService] Memproses Refund untuk {data['bookingId']}...")
        time.sleep(1)
        status = "Refunded" # E5: Refund Processed
        print("   -> Bank: Refund Successful.")

    # Broadcast Hasilnya ke SEMUA service (Fanout)
    result = {"bookingId": data['bookingId'], "status": status}
    channel.basic_publish(exchange='status_exchange', routing_key='', body=json.dumps(result))
    print(f" [x] Broadcast status '{status}' ke Status Exchange (Fanout)")

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue=queue_name, on_message_callback=callback)
print(' [*] Payment Service Waiting for requests...')
channel.start_consuming()
