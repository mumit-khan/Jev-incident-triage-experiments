# Sample synthetic incidents

These examples pair observation excerpts from the frozen inputs with their separate reference decisions. The references describe initial investigation, not model predictions or confirmed root causes. Counts and priority belong to the selected packet; other variations can differ.

## Power Fuse

Packet `NS-3717a233200d` · `test` · family `power_fuse`.

A blown DC distribution fuse isolates the radio and site router. Independent upstream probes show the aggregation node is healthy.

Service impact:

`{"affected_sites": 1, "basis": "Current independent service checks", "status": "outage"}`

Reference decisions:

`{"initial_owner": "power", "insufficient_evidence": "no", "next_check": "inspect_power", "priority": "P2"}`

## Noc Clear Only

Packet `NS-163edc67cb64` · `test` · family `noc_clear_only`.

The alarm cleared, but post-clear service measurements have not arrived. Recovery cannot yet be established from the available evidence.

Service impact:

`{"affected_sites": null, "basis": "Not independently verified", "status": "unknown"}`

Reference decisions:

`{"initial_owner": "noc", "insufficient_evidence": "yes", "next_check": "gather_evidence", "priority": "P3"}`

## Radio Neighbor

Packet `NS-50f2d4fcb9b6` · `test` · family `radio_neighbor`.

Mobility failures are restricted to a newly introduced neighbor relation. Stationary sessions and transport probes succeed.

Service impact:

`{"affected_sites": 2, "basis": "Current independent service checks", "status": "degraded"}`

Reference decisions:

`{"initial_owner": "ran", "insufficient_evidence": "no", "next_check": "inspect_radio", "priority": "P3"}`

## Power Controller

Packet `NS-c6144d55e07b` · `test` · family `power_controller`.

The power controller repeatedly opens the DC contactor despite healthy mains. Equipment resets align with the contactor events.

Service impact:

`{"affected_sites": 1, "basis": "Current independent service checks", "status": "degraded"}`

Reference decisions:

`{"initial_owner": "power", "insufficient_evidence": "no", "next_check": "inspect_power", "priority": "P3"}`

## Noc Postmaintenance

Packet `NS-5ad9c4ddef4b` · `test` · family `noc_postmaintenance`.

Planned work has ended. Independent service checks confirm sustained baseline performance for the full recovery observation interval; a delayed maintenance alarm is historical, not a current fault.

Service impact:

`{"affected_sites": 0, "basis": "Current independent service checks", "status": "none"}`

Reference decisions:

`{"initial_owner": "noc", "insufficient_evidence": "no", "next_check": "monitor", "priority": "P4"}`

## Core Certificate

Packet `NS-f45aa5858ae2` · `test` · family `core_certificate`.

Core service-to-service authentication fails after a certificate expired. Radio and transport checks pass on independent access paths.

Service impact:

`{"affected_sites": 12, "basis": "Current independent service checks", "status": "outage"}`

Reference decisions:

`{"initial_owner": "core", "insufficient_evidence": "no", "next_check": "inspect_core", "priority": "P1"}`

## Transport Qos

Packet `NS-948ed62ffbbf` · `test` · family `transport_qos`.

Only the expedited forwarding queue drops traffic on the common uplink. Other classes succeed and radio resource occupancy is normal.

Service impact:

`{"affected_sites": 9, "basis": "Current independent service checks", "status": "degraded"}`

Reference decisions:

`{"initial_owner": "transport", "insufficient_evidence": "no", "next_check": "inspect_transport", "priority": "P3"}`

## Core Signaling

Packet `NS-3f4de857ec84` · `test` · family `core_signaling`.

A shared core signaling worker queue is stalled. Requests from independent access paths reach it but are not processed.

Service impact:

`{"affected_sites": 18, "basis": "Current independent service checks", "status": "degraded"}`

Reference decisions:

`{"initial_owner": "core", "insufficient_evidence": "no", "next_check": "inspect_core", "priority": "P2"}`

## Noc Nearby

Packet `NS-5321254e60e7` · `test` · family `noc_nearby`.

Nearby sites report similar symptoms but have independent documented transport and power paths. No current domain-specific fault evidence is available.

Service impact:

`{"affected_sites": null, "basis": "Not independently verified", "status": "unknown"}`

Reference decisions:

`{"initial_owner": "noc", "insufficient_evidence": "yes", "next_check": "gather_evidence", "priority": "P3"}`

## Transport Asymmetry

Packet `NS-19cd88f8e238` · `test` · family `transport_asymmetry`.

Bidirectional probes show loss only on the return aggregation path. Radio processing and the outbound transport path are healthy.

Service impact:

`{"affected_sites": 12, "basis": "Current independent service checks", "status": "degraded"}`

Reference decisions:

`{"initial_owner": "transport", "insufficient_evidence": "no", "next_check": "inspect_transport", "priority": "P2"}`

## Radio Pim

Packet `NS-69782dcac43c` · `test` · family `radio_pim`.

Uplink interference tracks downlink transmit power on one sector. The shared transport path has clean counters and normal latency.

Service impact:

`{"affected_sites": 1, "basis": "Current independent service checks", "status": "degraded"}`

Reference decisions:

`{"initial_owner": "ran", "insufficient_evidence": "no", "next_check": "inspect_radio", "priority": "P3"}`

The [dataset card](dataset-card.md) explains construction and family variations. The [policy](policy.md) defines the outputs, and the [walkthrough guide](observatory.md) explains how to inspect complete packets and actual predictions.
