import demistomock as demisto  # noqa: F401
from CommonServerPython import *  # noqa: F401

from datetime import datetime, timezone
from typing import Any

# Severity mapping: XSOAR numeric severity -> XSIAM string severity
SEVERITY_MAP = {
    0: 'informational',
    1: 'low',
    2: 'medium',
    3: 'high',
    4: 'critical',
}


class XSIAMClient(BaseClient):
    """Client for the XSIAM Insert Parsed Alerts API."""

    def __init__(self, base_url: str, api_key: str, api_key_id: str, verify: bool, proxy: bool):
        headers = {
            'x-xdr-auth-id': api_key_id,
            'Authorization': api_key,
            'Content-Type': 'application/json',
        }
        super().__init__(
            base_url=base_url,
            verify=verify,
            proxy=proxy,
            headers=headers,
        )

    def insert_parsed_alerts(self, alerts: list) -> dict:
        """Push parsed alerts to XSIAM via the Insert Parsed Alerts API.

        Args:
            alerts: List of alert dicts conforming to the XSIAM parsed alert schema.

        Returns:
            Response dict from the XSIAM API.
        """
        body = {
            'request_data': {
                'alerts': alerts,
            }
        }
        demisto.debug(f'Inserting {len(alerts)} parsed alert(s) into XSIAM')
        return self._http_request(
            method='POST',
            url_suffix='/public_api/v1/alerts/insert_parsed_alerts',
            json_data=body,
        )


def map_severity(xsoar_severity: int) -> str:
    """Map XSOAR numeric severity to an XSIAM severity string.

    Args:
        xsoar_severity: Integer severity (0-4).

    Returns:
        XSIAM severity string.
    """
    return SEVERITY_MAP.get(xsoar_severity, 'informational')


def parse_date_to_epoch_ms(date_str: str | None) -> int:
    """Parse an ISO/date string to epoch milliseconds.

    Falls back to the current time if parsing fails or the input is empty.

    Args:
        date_str: Date string to parse (ISO format or common date string).

    Returns:
        Epoch time in milliseconds.
    """
    if not date_str:
        return int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    try:
        dt = arg_to_datetime(date_str)
        if dt:
            return int(dt.timestamp() * 1000)
    except Exception:
        demisto.debug(f'Failed to parse date string: {date_str}')
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def build_description(incident: dict) -> str:
    """Build a human-readable description string from an XSOAR incident.

    Includes the incident ID, type, status, owner, and description/details.

    Args:
        incident: XSOAR incident dict.

    Returns:
        Concatenated description string.
    """
    parts: list[str] = []

    incident_id = incident.get('id', '')
    if incident_id:
        parts.append(f'Incident ID: {incident_id}')

    inc_type = incident.get('type', '')
    if inc_type:
        parts.append(f'Type: {inc_type}')

    status_val = incident.get('status')
    if status_val is not None:
        # XSOAR status codes: 0=Active, 1=Done, 2=Archive
        status_names = {0: 'Active', 1: 'Done', 2: 'Archive'}
        parts.append(f'Status: {status_names.get(status_val, str(status_val))}')

    owner = incident.get('owner', '')
    if owner:
        parts.append(f'Owner: {owner}')

    details = incident.get('details', '')
    if details:
        parts.append(f'Details: {details}')

    description = incident.get('description', '')
    if description:
        parts.append(f'Description: {description}')

    return ' | '.join(parts)


def map_incident_to_alert(incident: dict) -> dict:
    """Map an XSOAR incident to an XSIAM parsed alert dict.

    Args:
        incident: XSOAR incident dict.

    Returns:
        Alert dict conforming to the XSIAM parsed alert schema.
    """
    event_timestamp = parse_date_to_epoch_ms(
        incident.get('occurred') or incident.get('created')
    )
    severity = map_severity(incident.get('severity', 0))

    return {
        'product': 'XSOAR',
        'vendor': 'Palo Alto Networks',
        'local_ip': '',
        'local_port': 0,
        'remote_ip': '',
        'remote_port': 0,
        'event_timestamp': event_timestamp,
        'severity': severity,
        'alert_name': incident.get('name', ''),
        'alert_description': build_description(incident),
    }


def search_incidents(query: str | None, max_incidents: int,
                     from_date: str | None = None, to_date: str | None = None) -> list[dict]:
    """Search XSOAR incidents using the getIncidents command.

    Handles pagination by fetching up to *max_incidents* results in batches.

    Args:
        query: XSOAR incident query string (optional).
        max_incidents: Maximum number of incidents to retrieve.
        from_date: Start date filter (ISO format, optional).
        to_date: End date filter (ISO format, optional).

    Returns:
        List of incident dicts.
    """
    args: dict[str, Any] = {
        'size': min(max_incidents, 100),
    }
    if query:
        args['query'] = query
    if from_date:
        args['fromdate'] = from_date
    if to_date:
        args['todate'] = to_date

    all_incidents: list[dict] = []
    page = 0

    while len(all_incidents) < max_incidents:
        args['page'] = page
        args['size'] = min(max_incidents - len(all_incidents), 100)
        demisto.debug(f'Searching incidents: page={page}, size={args["size"]}, query={query}')

        res = demisto.executeCommand('getIncidents', args)
        if is_error(res):
            raise DemistoException(f'Error searching incidents: {get_error(res)}')

        data = res[0].get('Contents', {}).get('data') or []
        if not data:
            break

        all_incidents.extend(data)
        if len(data) < args['size']:
            # Last page reached
            break
        page += 1

    return all_incidents[:max_incidents]


def push_incidents_command(client: XSIAMClient, args: dict, default_query: str | None,
                           default_max: int) -> CommandResults:
    """Execute the xsiam-push-incidents command.

    Args:
        client: XSIAMClient instance.
        args: Command arguments dict.
        default_query: Default query from integration params.
        default_max: Default max incidents from integration params.

    Returns:
        CommandResults with a summary table and context data.
    """
    query = args.get('query') or default_query
    max_incidents = arg_to_number(args.get('max_incidents')) or default_max
    from_date = args.get('from_date')
    to_date = args.get('to_date')

    incidents = search_incidents(query, max_incidents, from_date, to_date)
    if not incidents:
        return CommandResults(
            readable_output='No incidents found matching the query.',
            outputs_prefix='XSIAMPush',
            outputs={'PushedCount': 0, 'Incidents': []},
        )

    alerts = [map_incident_to_alert(inc) for inc in incidents]
    client.insert_parsed_alerts(alerts)

    pushed_summary = [
        {'ID': inc.get('id', ''), 'Name': inc.get('name', '')}
        for inc in incidents
    ]

    readable = tableToMarkdown(
        f'Successfully pushed {len(alerts)} incident(s) to XSIAM',
        pushed_summary,
        headers=['ID', 'Name'],
    )

    return CommandResults(
        readable_output=readable,
        outputs_prefix='XSIAMPush',
        outputs={
            'PushedCount': len(alerts),
            'Incidents': pushed_summary,
        },
    )


def push_single_incident_command(client: XSIAMClient, args: dict) -> CommandResults:
    """Execute the xsiam-push-incident command for a single incident.

    Args:
        client: XSIAMClient instance.
        args: Command arguments dict (must contain incident_id).

    Returns:
        CommandResults with details of the pushed incident.
    """
    incident_id = args.get('incident_id')
    if not incident_id:
        raise DemistoException('incident_id argument is required.')

    res = demisto.executeCommand('getIncidents', {'id': incident_id})
    if is_error(res):
        raise DemistoException(f'Error fetching incident {incident_id}: {get_error(res)}')

    data = res[0].get('Contents', {}).get('data') or []
    if not data:
        raise DemistoException(f'Incident {incident_id} not found.')

    incident = data[0]
    alert = map_incident_to_alert(incident)
    client.insert_parsed_alerts([alert])

    pushed_info = {
        'ID': incident.get('id', ''),
        'Name': incident.get('name', ''),
        'Severity': alert['severity'],
        'AlertName': alert['alert_name'],
    }

    readable = tableToMarkdown(
        f'Successfully pushed incident {incident_id} to XSIAM',
        pushed_info,
        headers=['ID', 'Name', 'Severity', 'AlertName'],
    )

    return CommandResults(
        readable_output=readable,
        outputs_prefix='XSIAMPush',
        outputs={'PushedIncident': pushed_info},
    )


def test_module(client: XSIAMClient) -> str:
    """Test connectivity to the XSIAM API by sending an empty alerts list.

    Args:
        client: XSIAMClient instance.

    Returns:
        'ok' on success.
    """
    client.insert_parsed_alerts([])
    return 'ok'


def main() -> None:
    params = demisto.params()
    command = demisto.command()
    args = demisto.args()

    base_url = params.get('url', '').rstrip('/')
    api_key = params.get('api_key', '')
    api_key_id = params.get('api_key_id', '')
    verify = not argToBoolean(params.get('insecure', False))
    proxy = argToBoolean(params.get('proxy', False))
    default_max = arg_to_number(params.get('max_incidents')) or 100
    default_query = params.get('query')

    demisto.debug(f'Command being called is {command}')

    try:
        client = XSIAMClient(
            base_url=base_url,
            api_key=api_key,
            api_key_id=api_key_id,
            verify=verify,
            proxy=proxy,
        )

        if command == 'test-module':
            result = test_module(client)
            return_results(result)

        elif command == 'xsiam-push-incidents':
            result = push_incidents_command(client, args, default_query, default_max)
            return_results(result)

        elif command == 'xsiam-push-incident':
            result = push_single_incident_command(client, args)
            return_results(result)

        else:
            raise NotImplementedError(f'Command {command} is not implemented.')

    except Exception as e:
        demisto.error(f'Failed to execute {command} command. Error: {str(e)}')
        return_error(f'Failed to execute {command} command.\nError:\n{str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
