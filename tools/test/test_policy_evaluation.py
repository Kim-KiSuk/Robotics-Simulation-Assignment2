import importlib.util
from hashlib import sha256
import json
from pathlib import Path
import shlex
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    'evaluation_summary', Path(__file__).parents[1] / 'summarize_policy_evaluation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def complete_log(outcomes):
    return '\n'.join(f'[INFO] Trial {i}: {value}' for i, value in enumerate(outcomes)) + (
        f'\nSuccessful trials: {sum(outcomes)}, out of {len(outcomes)} trials\n'
        f'Success rate: {sum(outcomes) / len(outcomes)}\n')


def test_exact_rate_requires_complete_consistent_trial_records():
    result = module.summarize(complete_log([True] * 37 + [False] * 63), 100)
    assert result['complete']
    assert result['policy_success_rate'] == .37
    assert result['observed_successes'] == 37


def test_partial_four_of_seven_is_not_a_hundred_trial_success_rate():
    log = complete_log([False, False, True, True, True, False, True])
    result = module.summarize(log, 100)
    assert not result['complete']
    assert result['completed_trials'] == 7 and result['observed_successes'] == 4
    assert result['policy_success_rate'] is None


@pytest.mark.parametrize('log', [
    complete_log([True, False]).replace('Trial 1', 'Trial 0'),
    complete_log([True, False]).replace('Successful trials: 1', 'Successful trials: 2'),
    complete_log([True, False]).replace('Success rate: 0.5', 'Success rate: 0.9'),
    complete_log([True, False]) + complete_log([True, False]),
    '[INFO] Trial 0: True\n[INFO] Trial 1: False\n',
    '',
])
def test_ambiguous_incomplete_or_inconsistent_logs_never_claim_success_rate(log):
    result = module.summarize(log, 2)
    assert not result['complete']
    assert result['policy_success_rate'] is None


@pytest.mark.parametrize('exitcode', [0, 7])
def test_wrapper_records_real_process_exit_and_checkpoint_identity(tmp_path, monkeypatch, exitcode):
    monkeypatch.setitem(sys.modules, 'summarize_policy_evaluation', module)
    runner_spec = importlib.util.spec_from_file_location(
        'evaluation_runner', Path(__file__).parents[1] / 'evaluate_experiment.py')
    runner = importlib.util.module_from_spec(runner_spec)
    runner_spec.loader.exec_module(runner)
    repo = tmp_path / 'repo'
    (repo / 'models').mkdir(parents=True)
    checkpoint = repo / 'models/test.pth'
    checkpoint.write_bytes(b'offline fixture, not a trained model')
    model_hash = sha256(checkpoint.read_bytes()).hexdigest()
    (repo / 'models/experiment_manifest.json').write_text(json.dumps({'models': [{
        'id': 'fixture', 'default_checkpoint': 'models/test.pth',
        'checkpoint_sha256': model_hash, 'training_seed': 101}]}))
    isaaclab = tmp_path / 'fake_launcher'
    isaaclab.mkdir()
    fixture = tmp_path / 'outcomes.txt'
    fixture.write_text(complete_log([True, False]))
    launcher = isaaclab / 'isaaclab.sh'
    launcher.write_text(f'#!/bin/sh\ncat {shlex.quote(str(fixture))}\nexit {exitcode}\n')
    launcher.chmod(0o755)
    monkeypatch.setattr(runner, 'REPO', repo)
    output = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', ['evaluate_experiment.py', '--experiment', 'fixture',
                                     '--isaaclab_root', str(isaaclab), '--num_rollouts', '2',
                                     '--output_root', str(output)])
    assert runner.main() == (0 if exitcode == 0 else 2)
    run_dir, = output.iterdir()
    result = json.loads((run_dir / 'results.json').read_text())
    metadata = json.loads((run_dir / 'metadata.json').read_text())
    assert result['checkpoint_sha256'] == model_hash == metadata['checkpoint_sha256']
    assert result['observed_successes'] == 1
    assert result['complete'] == (exitcode == 0)
    assert result['policy_success_rate'] == (.5 if exitcode == 0 else None)
    assert result['returncode'] == exitcode
    assert (run_dir / 'evaluation.log').read_text() == fixture.read_text()
