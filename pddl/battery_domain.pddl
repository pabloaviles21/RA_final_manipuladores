;;; =============================================================================
;;; battery_domain.pddl
;;; PDDL domain for the battery-swap manipulation task
;;;
;;; Robot:   UR3e with Robotiq gripper
;;; Planner: Fast Downward via ROS 2 downward_service
;;; TAMP:    The Kautham Project
;;;
;;; Requirements:
;;;   :adl encapsulates :strips :typing :equality :negative-preconditions
;;;        :disjunctive-preconditions :conditional-effects
;;;   Fast Downward compiles ADL to STRIPS internally (--translate-options).
;;; =============================================================================

(define (domain battery-swap)

  (:requirements :adl)

  (:types
    robot    ; the UR3e arm  (instance: ur3)
    object   ; manipulable items: box lid, batteries
    location ; named positions in the workspace
  )

  ;; ---------------------------------------------------------------------------
  ;; PREDICATES
  ;; ---------------------------------------------------------------------------
  (:predicates

    ;; Robot r is positioned at location l
    (at ?r - robot ?l - location)

    ;; Robot r's gripper is empty (not holding anything)
    (handEmpty ?r - robot)

    ;; Robot r is holding object o
    (holding ?r - robot ?o - object)

    ;; Object o is physically located at l
    (in ?o - object ?l - location)

    ;; The box lid has been moved aside → box interior is accessible
    (box_open)

    ;; Marks which object is the box lid (set in problem file)
    (is_lid ?o - object)

    ;; Marks the resting area where the lid goes when the box is open
    (is_lid_open_area ?l - location)

    ;; Marks locations that are inside the box (require box_open to access)
    (is_box_interior ?l - location)
  )

  ;; ---------------------------------------------------------------------------
  ;; ACTION: move
  ;; Free-motion transit of the robot from one location to another.
  ;; Corresponds to a "transit" motion in TAMP (no object carried).
  ;; ---------------------------------------------------------------------------
  (:action move
    :parameters (?r - robot ?from - location ?to - location)
    :precondition (and
      (at ?r ?from)
      (not (= ?from ?to))
    )
    :effect (and
      (at ?r ?to)
      (not (at ?r ?from))
    )
  )

  ;; ---------------------------------------------------------------------------
  ;; ACTION: pick
  ;; Robot grasps an object at its current location.
  ;; Corresponds to a transit→transfer transition in TAMP (close gripper).
  ;;
  ;; Constraint: If the object is inside the box (is_box_interior ?l),
  ;; the box must already be open.  This prevents picking the old battery
  ;; before the lid has been removed.
  ;; ---------------------------------------------------------------------------
  (:action pick
    :parameters (?r - robot ?o - object ?l - location)
    :precondition (and
      (at ?r ?l)
      (handEmpty ?r)
      (in ?o ?l)
      ;; imply(P, Q)  ≡  (¬P ∨ Q): if location is box interior, box must be open
      (imply (is_box_interior ?l) (box_open))
    )
    :effect (and
      (not (handEmpty ?r))
      (holding ?r ?o)
      (not (in ?o ?l))
    )
  )

  ;; ---------------------------------------------------------------------------
  ;; ACTION: place
  ;; Robot releases the held object at its current location.
  ;; Corresponds to a transfer→transit transition in TAMP (open gripper).
  ;;
  ;; Constraint: Placing inside the box also requires box_open.
  ;;
  ;; Conditional effects on the lid:
  ;;   • Placing the lid at is_lid_open_area  → sets   (box_open)
  ;;   • Placing the lid anywhere else        → resets (box_open)
  ;; ---------------------------------------------------------------------------
  (:action place
    :parameters (?r - robot ?o - object ?l - location)
    :precondition (and
      (at ?r ?l)
      (holding ?r ?o)
      ;; Cannot deposit inside a closed box
      (imply (is_box_interior ?l) (box_open))
    )
    :effect (and
      (not (holding ?r ?o))
      (handEmpty ?r)
      (in ?o ?l)

      ;; ── Lid placed at the open-area → box becomes open ──────────────────
      (when (and (is_lid ?o) (is_lid_open_area ?l))
        (box_open)
      )

      ;; ── Lid placed anywhere else (e.g. back on box) → box closes ────────
      (when (and (is_lid ?o) (not (is_lid_open_area ?l)))
        (not (box_open))
      )
    )
  )

)
