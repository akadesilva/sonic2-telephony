#!/usr/bin/env python3
"""
Evaluate agent sessions using AgentCore Evaluations.
Queries CloudWatch Logs and runs evaluations.
"""
import boto3
import json
import time
import argparse
from datetime import datetime, timedelta

def query_logs(logs_client, log_group_name, query_string, start_time, end_time):
    """Query CloudWatch Logs and return results."""
    query_id = logs_client.start_query(
        logGroupName=log_group_name,
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query_string
    )['queryId']
    
    # Wait for query to complete
    while True:
        result = logs_client.get_query_results(queryId=query_id)
        status = result['status']
        if status in ['Complete', 'Failed']:
            break
        time.sleep(1)
    
    if status == 'Failed':
        raise Exception(f"Query failed for log group: {log_group_name}")
    
    return result['results']

def extract_messages_as_json(query_results):
    """Extract JSON messages from query results."""
    messages = []
    for row in query_results:
        for field in row:
            if field['field'] == '@message' and field['value'].strip().startswith('{'):
                try:
                    messages.append(json.loads(field['value']))
                except json.JSONDecodeError:
                    continue
    return messages

def get_session_spans(region, log_group, session_id=None, hours_back=1):
    """Query CloudWatch Logs to get all spans for a session or all sessions."""
    logs_client = boto3.client('logs', region_name=region)
    
    start_time = datetime.now() - timedelta(hours=hours_back)
    end_time = datetime.now()
    
    # Build query with optional session filter
    if session_id:
        query = f"""fields @timestamp, @message   
        | filter ispresent(scope.name) and ispresent(attributes.session.id)
        | filter attributes.session.id = "{session_id}"
        | sort @timestamp asc"""
    else:
        query = """fields @timestamp, @message   
        | filter ispresent(scope.name) and ispresent(attributes.session.id)
        | sort @timestamp asc"""
    
    print(f"Querying log group: {log_group}")
    runtime_logs = query_logs(logs_client, log_group, query, start_time, end_time)
    print(f"  Found {len(runtime_logs)} runtime log entries")
    
    print(f"Querying log group: aws/spans")
    spans_logs = query_logs(logs_client, "aws/spans", query, start_time, end_time)
    print(f"  Found {len(spans_logs)} span entries")
    
    # Extract and combine
    all_spans = extract_messages_as_json(runtime_logs) + extract_messages_as_json(spans_logs)
    print(f"Total spans extracted: {len(all_spans)}")
    
    return all_spans

def evaluate_session(region, evaluator_id, session_spans, trace_ids=None, span_ids=None):
    """Run evaluation on session spans."""
    client = boto3.client('bedrock-agentcore', region_name=region)
    
    evaluation_input = {'sessionSpans': session_spans}
    
    kwargs = {
        'evaluatorId': evaluator_id,
        'evaluationInput': evaluation_input
    }
    
    # Add evaluation target if specified
    if trace_ids:
        kwargs['evaluationTarget'] = {'traceIds': trace_ids}
    elif span_ids:
        kwargs['evaluationTarget'] = {'spanIds': span_ids}
    
    print(f"\nRunning evaluation with {evaluator_id}...")
    response = client.evaluate(**kwargs)
    
    return response

def main():
    parser = argparse.ArgumentParser(description='Evaluate agent sessions')
    parser.add_argument('--session-id', help='Session ID to evaluate (optional - evaluates all if not provided)')
    parser.add_argument('--log-group', required=True, help='CloudWatch log group name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--evaluator', default='Builtin.Helpfulness', help='Evaluator ID')
    parser.add_argument('--trace-ids', nargs='+', help='Specific trace IDs to evaluate')
    parser.add_argument('--span-ids', nargs='+', help='Specific span IDs to evaluate')
    parser.add_argument('--hours-back', type=int, default=1, help='Hours to look back in logs')
    parser.add_argument('--save-spans', help='Save spans to JSON file')
    
    args = parser.parse_args()
    
    # Get spans from CloudWatch
    if args.session_id:
        print(f"Fetching spans for session: {args.session_id}")
    else:
        print(f"Fetching ALL spans from log group (last {args.hours_back} hours)")
    
    all_spans = get_session_spans(
        args.region, 
        args.log_group, 
        args.session_id,
        args.hours_back
    )
    
    if not all_spans:
        print("ERROR: No spans found")
        return 1
    
    # Group spans by session ID
    sessions = {}
    for span in all_spans:
        session_id = span.get('attributes', {}).get('session.id')
        if session_id:
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(span)
    
    print(f"\nFound {len(sessions)} unique session(s)")
    
    # Optionally save spans
    if args.save_spans:
        with open(args.save_spans, 'w') as f:
            json.dump(all_spans, f, indent=2)
        print(f"All spans saved to: {args.save_spans}")
    
    # Evaluate each session separately
    results = []
    for idx, (session_id, session_spans) in enumerate(sessions.items(), 1):
        print(f"\n{'='*80}")
        print(f"Evaluating session {idx}/{len(sessions)}: {session_id}")
        print(f"  Spans: {len(session_spans)}")
        print(f"{'='*80}")
        
        try:
            result = evaluate_session(
                args.region,
                args.evaluator,
                session_spans,
                args.trace_ids,
                args.span_ids
            )
            results.append({
                'session_id': session_id,
                'status': 'success',
                'result': result
            })
            
            # Display result
            print("\n📊 RESULT:")
            print(json.dumps(result, indent=2, default=str))
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            results.append({
                'session_id': session_id,
                'status': 'error',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'error')
    print(f"Total sessions: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    exit(main())
