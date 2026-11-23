# aircraft_performance.json

Données de performance de 11 avions de ligne (Airbus et Boeing) pour des calculs de décollage et de montée. Unités SI sauf indication contraire.

## Structure

Le fichier contient deux clés : `aircraft`, un objet indexé par nom d'avion (`"A320neo"`, `"B777-300ER"`...), et `sources`, la liste commune des références.

Chaque avion contient :

- `engine` : motorisation retenue.
- `geometric_aerodynamic`
  - `wing_reference_area` : surface alaire de référence (m²).
  - `CL_max` : coefficient de portance maximal en configuration décollage, déduit du V2.
  - `CD0` : traînée à portance nulle, en `takeoff` (volets et train sortis) et `clean`.
  - `K` : coefficient de traînée induite (CD = CD0 + K·CL²), en `takeoff` et `clean`.
  - `K_VS1g_min` : rapport V2/VS1g minimal réglementaire (1,13).
- `propulsion`
  - `number_of_engines` : nombre de moteurs.
  - `F_TO_base` : poussée max décollage par moteur (N).
  - `F_climb_base` : poussée max continue par moteur (N), utilisée pour la montée.
  - `T_flat` : température de flat rating (°C) en `takeoff` et `climb`. Au-dessus, la poussée diminue.
  - `k_derate_TO` / `k_derate_climb` : perte de poussée par degré au-dessus de `T_flat` (N/°C par moteur). `t_max_reduced_thrust` donne la température maximale de poussée réduite et la réduction maximale autorisée.
- `operational`
  - `operating_empty_weight` / `max_takeoff_weight` : masse à vide en opération et masse max au décollage (kg).
  - `rolling_friction_coefficient` : coefficient de frottement de roulement sur piste sèche.

## Champs annexes

Chaque valeur peut porter ces champs :

- `value`, `unit` : la valeur et son unité.
- `sources` : numéros renvoyant à la liste `sources` en fin de fichier.
- `derived` : `true` si la valeur est calculée plutôt que publiée. `method` donne alors la formule.
- `note` : hypothèse ou réserve sur la valeur.
- `isa_deviation` : écart à l'atmosphère standard (ISA+x) pour les températures.
