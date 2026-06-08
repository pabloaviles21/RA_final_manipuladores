;;; =============================================================================
;;; battery_problem.pddl
;;; PDDL problem instance for the battery-swap task
;;;
;;; Task narrative:
;;;   The UR3e must (1) open the box by moving the lid aside,
;;;   (2) remove the old battery and discard it, (3) pick the new battery
;;;   from its storage tray and install it inside the box, (4) close the box
;;;   by replacing the lid, and (5) return to home.
;;;
;;; Workspace layout (all positions are symbolic; physical coordinates
;;; are defined inside the Kautham problem file / tampconfig_battery.xml):
;;;
;;;          [battery_storage]       [discard_area]
;;;
;;;                    [box_closed_pos]   ← lid sits here when closed
;;;                    [lid_open_area]    ← lid rests here when open
;;;                    [inside_box]       ← battery slot inside the box
;;;
;;;          [home]                              ← robot rest pose
;;; =============================================================================

(define (problem battery-swap-p1)

  (:domain battery-swap)

  ;; ---------------------------------------------------------------------------
  ;; OBJECTS
  ;; ---------------------------------------------------------------------------
  (:objects
    ur3              - robot    ; the UR3e arm

    ; Manipulable objects
    box_lid          - object   ; the lid of the battery compartment
    battery_old      - object   ; the depleted battery to be removed
    battery_new      - object   ; the fresh battery to be installed

    ; Named workspace locations
    home             - location ; robot safe/home position
    box_closed_pos   - location ; where the lid sits when the box is closed
    lid_open_area    - location ; where the lid is placed while box is open
    inside_box       - location ; interior of the box (battery slot)
    battery_storage  - location ; tray / holder where battery_new starts
    discard_area     - location ; disposal zone for battery_old
  )

  ;; ---------------------------------------------------------------------------
  ;; INITIAL STATE
  ;; ---------------------------------------------------------------------------
  (:init

    ;; ── Robot ──────────────────────────────────────────────────────────────
    (at ur3 home)
    (handEmpty ur3)

    ;; ── Object positions ───────────────────────────────────────────────────
    (in box_lid         box_closed_pos)   ; lid is ON the box (box closed)
    (in battery_old     inside_box)       ; old battery is inside the box
    (in battery_new     battery_storage)  ; new battery is in the storage tray

    ;; ── Domain flags ───────────────────────────────────────────────────────
    ; (box_open) is intentionally ABSENT → box starts closed.
    ; battery_old cannot be picked until box_open is achieved.

    ;; ── Semantic markers (fixed, never modified by actions) ────────────────
    (is_lid          box_lid)             ; box_lid is "the lid"
    (is_lid_open_area lid_open_area)      ; lid_open_area triggers box_open
    (is_box_interior  inside_box)         ; inside_box requires box_open
  )

  ;; ---------------------------------------------------------------------------
  ;; GOAL STATE
  ;; ---------------------------------------------------------------------------
  (:goal (and

    ;; 1. Old battery has been discarded
    (in battery_old discard_area)

    ;; 2. New battery is installed inside the box
    (in battery_new inside_box)

    ;; 3. Lid has been replaced (box is closed again)
    (in box_lid box_closed_pos)

    ;; 4. Robot hand is empty
    (handEmpty ur3)

    ;; 5. Robot is back at home (optional; remove if planner struggles)
    (at ur3 home)
  ))

  ;; ---------------------------------------------------------------------------
  ;; METRIC (optional – uncomment if you want to minimize plan length)
  ;; ---------------------------------------------------------------------------
  ; (:metric minimize (total-cost))

)
