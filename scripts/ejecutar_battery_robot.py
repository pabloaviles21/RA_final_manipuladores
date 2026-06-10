import csv
import math
import socket
import time

HOST = "10.10.73.238"
PORT = 30002

CSV_FILE = "lab_controls.csv"

Abrir_pinza = "pinza40UR3.py"   # abre a 40 mm
Cerrar_pinza = "pinza10UR3.py"  # cierra a 10 mm

ACC = 0.25
VEL = 0.12


def cargar_posiciones(csv_path):
    posiciones = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            name = row["name"].strip()
            unit = row["unit"].strip().lower()

            q = [float(row[f"j{i}"]) for i in range(1, 7)]

            if unit in ("deg", "degree", "degrees", "grados"):
                q = [math.radians(x) for x in q]
            elif unit in ("rad", "radian", "radians", "radianes"):
                pass
            else:
                raise ValueError(f"Unidad no reconocida en {name}: {unit}")

            posiciones[name] = q

    return posiciones


def enviar_movej(sock, q, nombre):
    print(f"\n=== MOVIMIENTO: {nombre} ===")
    print([round(x, 4) for x in q])

    cmd = f"movej({q}, a={ACC}, v={VEL})\n"
    sock.sendall(cmd.encode())

    print("Esperando a que el robot llegue.")
    input("Cuando el robot haya acabado el movimiento, pulsa ENTER para continuar...")


def enviar_pinza(sock, archivo, accion):
    print(f"\n=== PINZA: {accion} ===")
    input("Pulsa ENTER para enviar este comando de pinza...")

    with open(archivo, "rb") as f:
        sock.sendall(f.read())

    print("Comando de pinza enviado.")
    time.sleep(3.0)
    input("Cuando la pinza haya acabado, pulsa ENTER para continuar...")


def coger(sock, posiciones, punto_pick, nombre_objeto):
    home = posiciones["C_HOME_SAFE"]
    pick = posiciones[punto_pick]

    enviar_movej(sock, home, "ir a HOME seguro")
    enviar_movej(sock, pick, f"ir a coger {nombre_objeto}")
    enviar_pinza(sock, Cerrar_pinza, f"cerrar pinza sobre {nombre_objeto}")
    enviar_movej(sock, home, f"volver a HOME con {nombre_objeto}")


def dejar(sock, posiciones, punto_place, nombre_destino):
    home = posiciones["C_HOME_SAFE"]
    place = posiciones[punto_place]

    enviar_movej(sock, home, "ir a HOME seguro")
    enviar_movej(sock, place, f"ir a dejar en {nombre_destino}")
    enviar_pinza(sock, Abrir_pinza, f"abrir pinza en {nombre_destino}")
    enviar_movej(sock, home, f"volver a HOME desde {nombre_destino}")


def main():
    posiciones = cargar_posiciones(CSV_FILE)

    print("Conectando con el robot...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print("Conectado.")

    try:
        print("\nIMPORTANTE:")
        print("Este script es manual: después de cada movimiento tienes que pulsar ENTER.")
        print("Si ves riesgo de choque, NO pulses ENTER y para el robot.")

        input("\nPulsa ENTER para empezar...")

        # Opcional: asegurar pinza abierta al principio
        enviar_pinza(sock, Abrir_pinza, "abrir pinza inicial")

        # 1. Abrir caja: coger tapa y dejarla apartada
        coger(sock, posiciones, "C_BOX_LID_PICK", "tapa inicial")
        dejar(sock, posiciones, "C_LID_OPEN_PLACE", "zona tapa abierta")

        # 2. Sacar batería vieja
        coger(sock, posiciones, "C_BATTERY_OLD_PICK", "batería vieja")
        dejar(sock, posiciones, "C_USED_PLACE", "caja de usadas")

        # 3. Coger batería nueva y ponerla dentro
        coger(sock, posiciones, "C_BATTERY_NEW_PICK", "batería nueva")
        dejar(sock, posiciones, "C_INSIDE_PLACE", "interior del aparato")

        # 4. Cerrar tapa
        coger(sock, posiciones, "C_LID_OPEN_PLACE", "tapa apartada")
        dejar(sock, posiciones, "C_BOX_LID_PICK", "posición tapa cerrada")

        print("\nSecuencia finalizada.")

    finally:
        sock.close()
        print("Socket cerrado.")


if __name__ == "__main__":
    main()
