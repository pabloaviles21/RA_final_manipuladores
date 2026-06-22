(define (problem battery-swap-p1)

  (:domain battery-swap)

;; Las cajas y zonas fijas se modelan como locations y no como objects, porque el robot no las recoge ni las desplaza.
  (:objects
    ur3 - robot
   
    box_lid - object
    battery_old - object
    battery_new - object

    box_closed_pos - location
    lid_open_area - location
    inside_box - location
    battery_storage - location
    discard_area - location
  )

;; Estado inicial de la tarea: caja cerrada, batería vieja dentro y batería nueva disponible en la zona de nuevas.
  (:init
    (handEmpty ur3)

    (in box_lid box_closed_pos)
    (in battery_old inside_box)
    (in battery_new battery_storage)

    (clear lid_open_area)
    (clear discard_area)

    (is_lid box_lid)
    (is_lid_open_area lid_open_area)
    (is_box_closed_pos box_closed_pos)
    (is_box_interior inside_box)

  )
;; Objetivo: sustituir la batería, descartar la antigua, cerrar de nuevo la caja y dejar la mano del robot libre.
  (:goal (and
    (in battery_old discard_area)
    (in battery_new inside_box)
    (in box_lid box_closed_pos)
    (handEmpty ur3)
  ))
)
