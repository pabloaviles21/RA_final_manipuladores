(define (domain battery-swap)

  (:requirements :adl :typing :equality)

  (:types
    robot
    object
    location
  )

  (:predicates
    (handEmpty ?r - robot)
    (holding ?r - robot ?o - object)
    (in ?o - object ?l - location)
    (clear ?l - location)

    (box_open)

   ;; Estos predicados son especificos para el robot (caja).
   ;; Permiten modelar que el interior solo es accesible cuando la tapa ha sido retirada.

    (is_lid ?o - object)
    (is_lid_open_area ?l - location)
    (is_box_closed_pos ?l - location)
    (is_box_interior ?l - location)
  )
;; Coger un objeto. Si el objeto está dentro de la caja,
;; la acción solo es válida cuando la caja está abierta.

  (:action pick
    :parameters (?r - robot ?o - object ?l - location)
    :precondition (and
      (handEmpty ?r)
      (in ?o ?l)
      (imply (is_box_interior ?l) (box_open))
    )
    :effect (and
      (not (handEmpty ?r))
      (holding ?r ?o)
      (not (in ?o ?l))
      (clear ?l)
    )
  )

;; Dejar un objeto. Colocar la tapa en la zona de apertura abre la caja,
;; colocarla en la posición cerrada vuelve a cerrar la caja.

  (:action place
    :parameters (?r - robot ?o - object ?l - location)
    :precondition (and
      (holding ?r ?o)
      (clear ?l)
      (imply (is_box_interior ?l) (box_open))
    )
    :effect (and
      (not (holding ?r ?o))
      (handEmpty ?r)
      (in ?o ?l)
      (not (clear ?l))

      (when (and (is_lid ?o) (is_lid_open_area ?l))
        (box_open)
      )

      (when (and (is_lid ?o) (is_box_closed_pos ?l))
        (not (box_open))
      )
    )
  )
)
