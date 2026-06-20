(define (problem battery-swap-p1)

  (:domain battery-swap)

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

    ;; La caja empieza cerrada: NO ponemos (box_open)
  )

  (:goal (and
    (in battery_old discard_area)
    (in battery_new inside_box)
    (in box_lid box_closed_pos)
    (handEmpty ur3)
  ))
)
