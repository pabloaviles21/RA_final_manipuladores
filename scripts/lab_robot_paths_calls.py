send_joint_path(path_1_go_pick_lid, sock)
# Cerrar pinza
with open(Cerrar_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_2_go_place_lid, sock)
# Abrir pinza
with open(Abrir_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_3_go_pick_old_battery, sock)
# Cerrar pinza
with open(Cerrar_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_4_go_place_old_battery, sock)
# Abrir pinza
with open(Abrir_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_5_go_pick_new_battery, sock)
# Cerrar pinza
with open(Cerrar_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_6_go_place_new_battery, sock)
# Abrir pinza
with open(Abrir_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_7_go_pick_lid_again, sock)
# Cerrar pinza
with open(Cerrar_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)

send_joint_path(path_8_go_close_lid, sock)
# Abrir pinza
with open(Abrir_pinza, 'rb') as f: sock.sendall(f.read())
time.sleep(1)
