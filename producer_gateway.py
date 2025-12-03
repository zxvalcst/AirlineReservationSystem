import pika
import json
import os
import time
import sys

# --- KONFIGURASI ---
USER_DB = 'users.json'
RABBIT_HOST = 'localhost'

# --- UTILITIES ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("="*50)
    print("   ✈️   AIRLINE RESERVATION SYSTEM - GATEWAY   ✈️")
    print("="*50)

def load_users():
    if not os.path.exists(USER_DB):
        return {}
    with open(USER_DB, 'r') as f:
        try: return json.load(f)
        except: return {}

def save_user(username, password):
    users = load_users()
    if username in users:
        return False # User sudah ada
    users[username] = password
    with open(USER_DB, 'w') as f:
        json.dump(users, f, indent=4)
    return True

# --- RABBITMQ PUBLISHER ---
def send_event(routing_key, payload):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBIT_HOST))
        channel = connection.channel()
        channel.exchange_declare(exchange='booking_exchange', exchange_type='direct')
        
        message = json.dumps(payload)
        channel.basic_publish(exchange='booking_exchange', routing_key=routing_key, body=message)
        
        print(f"\n [✓] Event sent to Backend: {routing_key}")
        print(f" [i] Payload: {message}")
        connection.close()
        return True
    except Exception as e:
        print(f"\n [X] Gagal terhubung ke RabbitMQ: {e}")
        return False

# --- MENUS ---

def menu_dashboard(username):
    while True:
        print_header()
        print(f"👋 Selamat Datang, {username}!")
        print("-" * 50)
        print("1. 🎫  Pesan Tiket (Make Payment)")
        print("2. ❌  Batalkan Tiket (Cancel Ticket)")
        print("3. 🚪  Logout")
        print("-" * 50)
        
        choice = input("Pilih menu (1-3): ")

        if choice == '1':
            print("\n--- FORMULIR PEMESANAN ---")
            booking_id = input("Masukkan Booking ID (misal B-1002): ")
            amount = input("Masukkan Jumlah Pembayaran (Rp): ")
            
            # Validasi input angka
            try: amount = int(amount)
            except: amount = 0

            payload = {
                "bookingId": booking_id,
                "passenger": username,
                "amount": amount,
                "paymentMethod": "CreditCard", # Hardcode untuk simulasi
                "timestamp": time.time()
            }
            
            # E1: Booking Submitted
            send_event('booking.submit', payload)
            input("\nTekan Enter untuk kembali...")

        elif choice == '2':
            print("\n--- FORMULIR PEMBATALAN ---")
            booking_id = input("Masukkan Booking ID yang mau dibatalkan: ")
            reason = input("Alasan pembatalan: ")

            payload = {
                "bookingId": booking_id,
                "passenger": username,
                "reason": reason,
                "timestamp": time.time()
            }

            # Initiating Cancellation
            send_event('booking.cancel_request', payload)
            input("\nTekan Enter untuk kembali...")

        elif choice == '3':
            print("Logging out...")
            time.sleep(1)
            break
        else:
            input("Pilihan tidak valid!")

def menu_main():
    while True:
        print_header()
        print("   CONTROL PANEL LOGIN")
        print("-" * 50)
        print("1. 🔐 Login")
        print("2. 📝 Register User Baru")
        print("3. 🚶 Keluar Aplikasi")
        print("-" * 50)
        
        choice = input("Pilih menu (1-3): ")

        if choice == '1':
            user = input("\nUsername : ")
            pwd  = input("Password : ")
            
            users = load_users()
            if user in users and users[user] == pwd:
                print("\nLogin Berhasil! Masuk ke dashboard...")
                time.sleep(1)
                menu_dashboard(user)
            else:
                print("\n[!] Login Gagal: Username atau Password salah.")
                input("Tekan Enter untuk mencoba lagi...")

        elif choice == '2':
            print("\n--- REGISTER USER ---")
            new_user = input("Buat Username : ")
            new_pwd  = input("Buat Password : ")
            
            if new_user and new_pwd:
                if save_user(new_user, new_pwd):
                    print(f"\n[✓] User '{new_user}' berhasil didaftarkan!")
                else:
                    print(f"\n[!] Gagal: Username '{new_user}' sudah terpakai.")
            else:
                print("\n[!] Username/Password tidak boleh kosong.")
            
            input("Tekan Enter untuk kembali...")

        elif choice == '3':
            print("\nTerima kasih telah menggunakan sistem ini. Bye!")
            sys.exit()

if __name__ == "__main__":
    try:
        menu_main()
    except KeyboardInterrupt:
        print("\nForce Close.")