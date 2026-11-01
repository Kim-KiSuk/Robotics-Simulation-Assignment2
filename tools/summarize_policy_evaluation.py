"""Validate recorded play.py outcomes; never infer success from video duration."""

import argparse
import json
import re
from pathlib import Path


def summarize(text, expected_trials=None):
    trials = [(int(index), value == 'True') for index, value in re.findall(
        r'^\[INFO\] Trial (\d+): (True|False)\s*$', text, re.MULTILINE)]
    summaries = re.findall(r'Successful trials:\s*(\d+), out of (\d+) trials', text)
    rates = re.findall(r'^Success rate:\s*([0-9.eE+\-]+)\s*$', text, re.MULTILINE)
    errors = []
    indices = [index for index, _ in trials]
    if indices != list(range(len(trials))):
        errors.append('Trial indices must be unique, contiguous, and start at zero.')
    if len(summaries) != 1 or len(rates) != 1:
        errors.append('Exactly one final count and success-rate summary are required.')
    observed = sum(value for _, value in trials)
    reported = None
    if len(summaries) == 1:
        reported_successes, total = map(int, summaries[0])
        reported = {'successes': reported_successes, 'trials': total}
        if total != len(trials) or reported_successes != observed:
            errors.append('Final summary does not match per-trial outcomes.')
        if total <= 0:
            errors.append('At least one completed trial is required.')
        if len(rates) == 1 and total > 0:
            if abs(float(rates[0]) - reported_successes / total) > 1e-6:
                errors.append('Printed rate does not match the final count.')
    if expected_trials is not None and len(trials) != expected_trials:
        errors.append(f'Expected {expected_trials} trials, found {len(trials)}.')
    complete = not errors
    return {
        'complete': complete,
        'requested_trials': expected_trials,
        'completed_trials': len(trials),
        'observed_successes': observed,
        'policy_success_rate': observed / len(trials) if complete else None,
        'reported_summary': reported,
        'validation_errors': errors,
        'trials': [{'trial': index, 'success': value} for index, value in trials],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--expected_trials', type=int, default=100)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = summarize(args.log.read_text(errors='replace'), args.expected_trials)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            stream.write(encoded)
    print(encoded, end='')
    return 0 if result['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
