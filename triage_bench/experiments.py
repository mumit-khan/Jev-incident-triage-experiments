"""Validation-driven representations. No label or family metadata enters a request."""
from datetime import datetime

from .policy import OPTIONS


def impact_band(impact):
    n = impact.get('affected_sites')
    if n is None:
        return 'unknown'
    if n == 0:
        return 'zero'
    return 'one_to_nine' if n < 10 else 'ten_or_more'


def compact_packet(packet):
    # Keep current observations, not a duplicate ticket summary or generated IDs.
    observations = []
    now = datetime.fromisoformat(packet['decision_timestamp'].replace('Z', '+00:00'))
    for obs in packet['observations']:
        reported = datetime.fromisoformat(obs['observed_at'].replace('Z', '+00:00'))
        observations.append({'detail': obs['detail'],
                             'report_age_minutes': (now - reported).total_seconds() / 60})
    return {'service_impact': {**packet['service_impact'],
                              'affected_sites_band': impact_band(packet['service_impact'])},
            'observations': observations, 'change_record': packet['change_record'],
            'topology': packet['topology'],
            'evidence_note': 'Report age is when a report arrived. A report can describe a stale measurement. Topology is inventory, not proof of a fault.'}


def focused_questions():
    options = {f: dict(c) for f, c in OPTIONS.items()}
    options['initial_owner'].update({
        'ran': 'Observed radio-access performance or hardware malfunction: scheduling, RF reception, antenna, interference, timing or mobility.',
        'noc': 'No domain is supported by current evidence, or evidence is stale/conflicting; also verified recovery or fully explained maintenance.'})
    options['next_check']['verify_change'] = 'A change or maintenance scope is relevant but does not explain all observed impact; first verify scope and timing. Do not roll back.'
    instructions = {
        'initial_owner': 'Choose the first investigating team using observations. This is NOT confirmed root cause. A directly observed malfunction is enough to begin domain investigation even if its exact cause is unknown. Do not infer a transport fault from inventory edges alone. Unexplained maintenance scope stays with noc. Verified recovery stays with noc.',
        'priority': 'Apply ONLY service_impact.status and affected_sites_band. outage + ten_or_more => P1; outage + one_to_nine => P2; degraded + ten_or_more => P2; degraded + one_to_nine => P3; unknown => P3; none => P4. Do not use fault type or alarm severity.',
        'next_check': 'Choose the next diagnostic, using observations and this policy. Directly observed domain malfunction supports that domain diagnostic without proving root cause. If a maintenance/change scope is relevant but unexplained, choose verify_change. If other evidence is missing, stale or conflicting, choose gather_evidence. If recovery is independently verified or maintenance fully explains impact, choose monitor. Topology inventory alone does not prove transport failure.',
        'insufficient_evidence': 'Is current evidence insufficient to choose an initial investigating domain under the policy? Unknown exact root cause is NOT enough for yes. A directly observed domain malfunction is sufficient for no. Unexplained maintenance impact, stale measurements or conflicting evidence mean yes. Verified recovery or fully explained maintenance means no.'}
    return {f: {'type': 'choice', 'instructions': instructions[f], 'criteria': options[f]} for f in OPTIONS}


def structured_features(packet):
    impact = packet['service_impact']
    band = impact_band(impact)
    return {'impact_status': impact['status'], 'affected_sites_band': band,
            'status_and_band': impact['status'] + '/' + band}
