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

    (is_lid ?o - object)
    (is_lid_open_area ?l - location)
    (is_box_closed_pos ?l - location)
    (is_box_interior ?l - location)
  )

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
