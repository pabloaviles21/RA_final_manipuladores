# Proyecto Final RA – Battery Swap con UR3e

Robot: UR3e + Robotiq 2F-85  
Stack: ROS 2 Jazzy · The Kautham Project · Fast Downward (`downward_service`) · TAMP

---

## A. Diseño simbólico de la tarea

### Descripción narrativa

El robot UR3e debe realizar un cambio de batería en una caja con tapa:

1. **Abrir la caja** moviendo la tapa desde su posición cerrada (`box_closed_pos`)
   hasta la zona de aparcamiento del lado (`lid_open_area`).
2. **Extraer la batería vieja** cogiendo `battery_old` de `inside_box`
   y depositándola en `discard_area`.
3. **Instalar la batería nueva** cogiendo `battery_new` de `battery_storage`
   y colocándola en `inside_box`.
4. **Cerrar la caja** cogiendo la tapa de `lid_open_area`
   y volviendo a colocarla en `box_closed_pos`.

### Secuencias pick-move-place (≥ 2 requeridas, aquí hay 4)

| # | Pick desde          | Place en            | Objeto        |
|---|---------------------|---------------------|---------------|
| 1 | `box_closed_pos`    | `lid_open_area`     | `box_lid`     |
| 2 | `inside_box`        | `discard_area`      | `battery_old` |
| 3 | `battery_storage`   | `inside_box`        | `battery_new` |
| 4 | `lid_open_area`     | `box_closed_pos`    | `box_lid`     |

### Modelo simbólico – predicados clave

| Predicado             | Tipo                        | Significado                               |
|-----------------------|-----------------------------|-------------------------------------------|
| `(at ?r ?l)`          | fluente                     | robot `?r` está en localización `?l`      |
| `(handEmpty ?r)`      | fluente                     | mano vacía                                |
| `(holding ?r ?o)`     | fluente                     | robot sujeta el objeto `?o`               |
| `(in ?o ?l)`          | fluente                     | objeto `?o` está en localización `?l`     |
| `(box_open)`          | fluente (sin parámetros)    | la tapa ha sido quitada                   |
| `(is_lid ?o)`         | estático                    | `?o` es la tapa de la caja               |
| `(is_lid_open_area ?l)`| estático                   | `?l` dispara `box_open` al depositar tapa |
| `(is_box_interior ?l)`| estático                    | `?l` requiere `box_open` para acceder     |

### Restricción principal

`battery_old` no puede cogerse hasta que `(box_open)` sea verdadero.
El predicado `(box_open)` se activa como efecto condicional de la acción
`place` cuando se coloca `box_lid` en `is_lid_open_area`.
Se usa `(imply (is_box_interior ?l) (box_open))` en las precondiciones de
`pick` y `place` para hacer cumplir la restricción genéricamente.

---

## B. Archivo PDDL de dominio

Fichero: `pddl/battery_domain.pddl`

```
Acciones:   move · pick · place
Requisitos: :adl  (Fast Downward compila ADL a STRIPS internamente)
```

El dominio es genérico: **no contiene nombres de objetos concretos**.
Los estáticos (`is_lid`, `is_lid_open_area`, `is_box_interior`) se inicializan
en el archivo de problema para mantener el dominio reutilizable.

---

## C. Archivo PDDL de problema

Fichero: `pddl/battery_problem.pddl`

```
Objetos:     ur3, box_lid, battery_old, battery_new
Localizaciones: home, box_closed_pos, lid_open_area,
                inside_box, battery_storage, discard_area
```

El estado inicial **no incluye `(box_open)`** → caja cerrada.
El estado final exige:  `battery_old ∈ discard_area`,  `battery_new ∈ inside_box`,
`box_lid ∈ box_closed_pos`,  `handEmpty ur3`,  `at ur3 home`.

---

## D. Tampconfig de Kautham

Fichero: `kautham/tampconfig_battery.xml`

Estructura en 3 secciones:

1. **`<Problemfiles>`** – ruta al fichero de escena Kautham (`.xml`).
2. **`<States>`** – configuraciones articulares con nombre (7 valores normalizados).
3. **`<Actions>`** – mapeo PDDL pick/place ↔ `HomeControls` + `GraspControls`.

Todos los valores de controls marcados `TODO` deben obtenerse con Kautham GUI
(ver sección F).

---

## E. Archivos de Kautham que hay que copiar / modificar

Basarse en la demo `chess_ur3_robotiq`.  Pasos sugeridos:

### 5.1. Fichero de escena Kautham (`.xml`)

```
chess_ur3_robotiq/
└── chess_ur3_robotiq.xml     →  kautham/battery_task.xml
```

Cambios en `battery_task.xml`:

| Elemento              | Qué cambiar                                               |
|-----------------------|-----------------------------------------------------------|
| `<Robot>`             | Mantener el UR3e + Robotiq.  Verificar rutas URDF.        |
| `<Obstacle>` / tabla  | Sustituir el tablero de ajedrez por la caja + tapa.       |
| `<Object>` para piezas| Sustituir por `battery_old`, `battery_new`, `box_lid`.    |
| Poses iniciales       | Ajustar las 7 coordenadas de cada objeto (ver sección F). |
| Nombre del robot      | Debe coincidir con el usado en `tampconfig_battery.xml`.  |

### 5.2. Fichero tampconfig

```
chess_ur3_robotiq/
└── tampconfig_chess.xml      →  kautham/tampconfig_battery.xml  (ya creado)
```

Cambios:
- Sustituir los `<State>` del ajedrez por los de la tarea de baterías.
- Sustituir los `<Action>` (mover piezas) por los 8 de esta tarea.
- Actualizar la ruta en `<Problemfile>`.

### 5.3. Archivos PDDL del paquete ROS

```
chess_ur3_robotiq/pddl/
├── chess_domain.pddl    →  pddl/battery_domain.pddl   (ya creado)
└── chess_problem.pddl   →  pddl/battery_problem.pddl  (ya creado)
```

### 5.4. Launch file ROS 2

```
chess_ur3_robotiq/launch/chess_tamp.launch.py
```

Copiar y modificar los parámetros:
- Rutas a los ficheros PDDL.
- Ruta a `tampconfig_battery.xml`.
- Nombre del servicio de Kautham si difiere.

### 5.3. Modelos 3D necesarios (nuevos)

Crear o descargar modelos URDF/STL para:

| Modelo          | Nombre sugerido       | Observación                                 |
|-----------------|-----------------------|---------------------------------------------|
| Caja            | `battery_box.urdf`    | Puede ser un paralelepípedo simple           |
| Tapa de la caja | `battery_lid.urdf`    | Objeto separado manipulable                 |
| Batería vieja   | `battery_old.urdf`    | Cilindro o paralelepípedo pequeño (AA/18650) |
| Batería nueva   | `battery_new.urdf`    | Idéntico al anterior (o color diferente)    |
| Bandeja descarte| `discard_tray.urdf`   | Puede ser un bloque plano                   |
| Bandeja almacén | `storage_tray.urdf`   | Ídem                                        |

---

## F. Valores que hay que buscar en Kautham (TODOs)

### F.1. Poses de los objetos en la escena (battery_task.xml)

Formato en Kautham scene file: `(TH, WZ, WY, WX, Z, Y, X)`

| Objeto / Punto   | Variable          | Cómo encontrarlo                                           |
|------------------|-------------------|------------------------------------------------------------|
| `box_closed_pos` | pose 3D de la tapa| Medir con regla / herramienta de poses de Kautham GUI      |
| `lid_open_area`  | pose 3D           | Elegir un punto estable al lado de la caja                 |
| `inside_box`     | pose 3D           | Centro del compartimento interior de la caja               |
| `battery_storage`| pose 3D           | Centro de la bandeja de almacenamiento                     |
| `discard_area`   | pose 3D           | Centro de la bandeja de descarte                           |
| `home`           | config articular  | Posición de reposo del UR3e (todos los joints ≈ 0 rad)     |

### F.2. Controles articulares (tampconfig_battery.xml)

Para cada `<State>` con valor `TODO`:

1. Abrir Kautham GUI y cargar `battery_task.xml`.
2. Usar el panel de IK para mover el TCP a la pose deseada, o mover sliders manualmente.
3. Anotar los 7 valores del panel **Controls** (j1..j6 + gripper), todos en [0,1].
4. Pegar en el campo `<Controls>` correspondiente.

**Fórmulas de normalización** (para verificación manual):

```
Joints 1, 2, 4, 5, 6:   q_norm = (q_rad + 2π) / 4π
Joint 3 (codo):          q_norm = (q_rad + π)  / 2π
Inversa:
Joints 1, 2, 4, 5, 6:   q_rad  = q_norm * 4π  − 2π
Joint 3 (codo):          q_rad  = q_norm * 2π  − π
```

### F.3. Nombre exacto del robot en Kautham

- Buscar el atributo `name` del elemento `<Robot>` en `battery_task.xml`.
- Debe coincidir con cualquier referencia en `tampconfig_battery.xml`.
- En el chess demo suele ser algo como `"ur3_robotiq"` o `"UR3e_2f85"`.

### F.4. Nombres exactos de los objetos en Kautham

Los nombres en el PDDL (`battery_old`, `battery_new`, `box_lid`) deben
coincidir con los nombres de los objetos en `battery_task.xml` tal y como
los ve el tamp_helper.  Verificar mirando los logs del nodo TAMP o el fichero
de configuración del tamp_helper.

### F.5. Offset de aproximación (pregrasp)

Típicamente 10-15 cm en Z sobre el objeto.  Ajustar para cada objeto según
la altura de la caja, bandeja, etc.  Si la caja es alta, el offset debe ser mayor.

### F.6. Apertura de pinza

El 7.º valor de controls es la apertura normalizada de la pinza Robotiq:
- `0.0` = completamente abierta
- `1.0` = completamente cerrada

Para cada objeto, comprobar experimentalmente el valor de cierre que sujeta
bien el objeto sin aplastarlo.  Valores típicos para una batería cilíndrica:
`0.6 – 0.75`.

---

## G. Plan simbólico esperado (Fast Downward)

El plan que debería generar `downward_service` para este problema es:

```
01  (move ur3 home box_closed_pos)
02  (pick ur3 box_lid box_closed_pos)
03  (move ur3 box_closed_pos lid_open_area)
04  (place ur3 box_lid lid_open_area)          ; → box_open = true
05  (move ur3 lid_open_area inside_box)
06  (pick ur3 battery_old inside_box)          ; requiere box_open ✓
07  (move ur3 inside_box discard_area)
08  (place ur3 battery_old discard_area)
09  (move ur3 discard_area battery_storage)
10  (pick ur3 battery_new battery_storage)
11  (move ur3 battery_storage inside_box)
12  (place ur3 battery_new inside_box)         ; requiere box_open ✓
13  (move ur3 inside_box lid_open_area)
14  (pick ur3 box_lid lid_open_area)
15  (move ur3 lid_open_area box_closed_pos)
16  (place ur3 box_lid box_closed_pos)         ; → box_open = false
17  (move ur3 box_closed_pos home)
```

**Total: 17 pasos** (8 picks/places + 9 moves).

### Criterios de validación del plan simbólico

- [ ] La primera acción es `move` (robot parte de `home`).
- [ ] Las acciones 2 y 4 forman la primera secuencia pick-move-place (tapa).
- [ ] La acción 6 aparece **después** de la acción 4 (no antes; `box_open` requerido).
- [ ] Las acciones 10 y 12 forman la tercera secuencia pick-move-place (batería nueva).
- [ ] La acción 12 aparece mientras `box_open` todavía es true (acción 16 no ha ocurrido).
- [ ] La acción 16 **cierra la caja** (la última `place` de la tapa).
- [ ] El plan termina con `move ur3 ... home`.
- [ ] Estado final: `(in battery_old discard_area)`, `(in battery_new inside_box)`,
      `(in box_lid box_closed_pos)`, `(handEmpty ur3)`, `(at ur3 home)`.

Fast Downward puede encontrar un plan diferente (p. ej. reordenando pasos
independientes) pero siempre debe respetar las dependencias anteriores.

---

## H. Cómo ejecutar y validar con ROS 2 y Kautham

### H.1. Verificar el plan simbólico (solo PDDL, sin Kautham)

```bash
# Opción A: validador local (VAL/PDDL4J)
validate pddl/battery_domain.pddl pddl/battery_problem.pddl

# Opción B: planificador online
# Subir los dos ficheros a editor.planning.domains o planning.domains
# y usar Fast Downward con --search "astar(blind())"

# Opción C: Fast Downward local
fast-downward pddl/battery_domain.pddl pddl/battery_problem.pddl \
  --search "astar(blind())"
```

### H.2. Ejecutar con downward_service en ROS 2

```bash
# Terminal 1: lanzar el servicio Fast Downward
ros2 run downward_service downward_service_node

# Terminal 2: llamar al servicio con los ficheros PDDL
ros2 service call /downward_service downward_msgs/srv/DownwardService \
  "{domain_file: '$(pwd)/pddl/battery_domain.pddl',
    problem_file: '$(pwd)/pddl/battery_problem.pddl'}"
```

La respuesta contendrá el plan en texto.  Verificar que tiene 17 pasos
(o similar) y que respeta las dependencias de `box_open`.

### H.3. Ejecutar TAMP completo con Kautham

```bash
# Terminal 1: Kautham GUI / servidor
ros2 launch kautham_ros kautham.launch.py \
  problem:=$(pwd)/kautham/battery_task.xml

# Terminal 2: nodo TAMP helper
ros2 launch tamp_helper tamp.launch.py \
  tampconfig:=$(pwd)/kautham/tampconfig_battery.xml \
  domain:=$(pwd)/pddl/battery_domain.pddl \
  problem:=$(pwd)/pddl/battery_problem.pddl
```

> **TODO**: Adaptar los nombres de launch files / parámetros al paquete
> exacto que tenéis instalado (puede variar entre versiones de Kautham).

### H.4. Comprobaciones en Kautham GUI durante TAMP

- [ ] Los objetos aparecen en las posiciones iniciales correctas.
- [ ] El robot alcanza cada pose de pregrasp sin colisión.
- [ ] Las trayectorias RRT conectan los estados de HomeControls y GraspControls.
- [ ] Tras la acción 4, el objeto `box_lid` se mueve visualmente a `lid_open_area`.
- [ ] El interior de la caja es accesible para el brazo tras quitar la tapa.
- [ ] La simulación completa devuelve un `taskfile_tampconfig_battery.xml`.

---

## I. Cómo pasar el taskfile al script Python del UR3e real

### I.1. Qué es el taskfile

El `taskfile_tampconfig_battery.xml` (generado por Kautham TAMP) contiene
la secuencia completa de configuraciones articulares que el robot debe seguir,
incluyendo tanto los tramos de **tránsito libre** (`transit`) como los de
**transporte de objeto** (`transfer`).

### I.2. Reglas de traducción

| Transición TAMP          | Acción gripper           | Comentario                     |
|--------------------------|--------------------------|--------------------------------|
| `transit` → `transfer`   | **Cerrar gripper** (pick) | Primero llegar, luego cerrar  |
| `transfer` → `transit`   | **Abrir gripper** (place) | Primero llegar, luego abrir   |
| Sin cambio de tipo       | Sin acción gripper        | Solo movimiento               |

**Invariante:** la secuencia siempre empieza y termina con `MOVE`.

### I.3. Conversión de valores normalizados a radianes

```python
import math
PI = math.pi

def norm_to_rad(q_norm: float, joint_idx: int) -> float:
    # joint_idx: 0-based (0=j1, 1=j2, 2=j3_elbow, 3=j4, 4=j5, 5=j6)
    if joint_idx == 2:            # elbow (joint 3)
        return q_norm * 2*PI - PI
    else:
        return q_norm * 4*PI - 2*PI
```

### I.4. Uso del script de conversión

```bash
# Modo seco (imprime secuencia sin conectar al robot)
python3 scripts/parse_taskfile.py taskfile_tampconfig_battery.xml --dry-run

# Ejecución real en el robot
python3 scripts/parse_taskfile.py taskfile_tampconfig_battery.xml \
  --robot-ip 192.168.1.100
```

### I.5. TODOs para el script de ejecución real

- [ ] Comprobar la estructura XML real del taskfile e **ajustar los XPath**
  en `parse_taskfile.py` (función `parse_taskfile`).  El nombre de los
  elementos (`<Step>`, `<Waypoint>`, `<Config>`, …) varía con la versión
  de Kautham.  Hacer `print(ET.tostring(root, encoding='unicode'))` para
  inspeccionar.
- [ ] Sustituir `192.168.1.100` por la IP real del UR3e.
- [ ] Implementar el control de la pinza Robotiq (I/O digital, driver ROS 2,
  o script URScript directo).
- [ ] Ajustar `DEFAULT_SPEED` y `DEFAULT_ACCEL` a valores seguros para la tarea.
- [ ] Añadir E-stop / safety checks antes de ejecutar en el robot real.
- [ ] Verificar que el primer y el último `MOVE` de la secuencia llevan el robot
  a la posición `home` (todos los joints ≈ 0 rad).

---

## Estructura del repositorio

```
RA_final_manipuladores/
├── Docu/
│   └── Practica Final.pdf
├── pddl/
│   ├── battery_domain.pddl      ← dominio PDDL (acciones move, pick, place)
│   └── battery_problem.pddl     ← problema PDDL (estado inicial y final)
├── kautham/
│   ├── tampconfig_battery.xml   ← config TAMP (TODO: rellenar Controls)
│   └── battery_task.xml         ← TODO: crear desde chess_ur3_robotiq.xml
├── scripts/
│   └── parse_taskfile.py        ← convierte taskfile → comandos UR3e
└── README.md                    ← este fichero
```
