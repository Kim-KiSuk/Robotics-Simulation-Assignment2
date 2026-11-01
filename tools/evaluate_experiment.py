"""Run one checkpoint and save its hash, command, console output, and validated outcomes."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from summarize_policy_evaluation import summarize


REPO = Path(__file__).resolve().parents[1]


def main():
    models = {row['id']: row for row in json.loads(
        (REPO / 'models/experiment_manifest.json').read_text())['models']}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', choices=sorted(models), required=True)
    parser.add_argument('--checkpoint', type=Path, help='Override the downloaded checkpoint path.')
    parser.add_argument('--isaaclab_root', type=Path, required=True)
    parser.add_argument('--output_root', type=Path, default=REPO / 'reports/evaluations')
    parser.add_argument('--num_rollouts', type=int, default=100)
    parser.add_argument('--horizon', type=int, default=800)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--video', action='store_true')
    args = parser.parse_args()
    if args.num_rollouts < 1 or args.horizon < 1:
        parser.error('num_rollouts and horizon must be positive.')
    model = models[args.experiment]
    checkpoint = (args.checkpoint or REPO / model['default_checkpoint']).resolve()
    root = args.isaaclab_root.resolve()
    if not checkpoint.is_file():
        parser.error(f'Checkpoint missing: {checkpoint}. Download the experiment Release or use --checkpoint.')
    if not (root / 'isaaclab.sh').is_file():
        parser.error(f'IsaacLab launcher missing: {root / "isaaclab.sh"}')
    actual_hash = sha256(checkpoint.read_bytes()).hexdigest()
    if actual_hash != model['checkpoint_sha256']:
        parser.error('Checkpoint SHA256 does not match the selected experiment manifest.')
    output = args.output_root.resolve() / (
        args.experiment + '_' + datetime.now().astimezone().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir(parents=True, exist_ok=False)
    command = [str(root / 'isaaclab.sh'), '-p',
               str(REPO / 'isaaclab_project/scripts/imitation_learning/robomimic/play.py'),
               '--task', 'Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0',
               '--checkpoint', str(checkpoint), '--num_rollouts', str(args.num_rollouts),
               '--horizon', str(args.horizon), '--seed', str(args.seed)]
    if args.headless:
        command.append('--headless')
    if args.video:
        command.extend(['--video', '--video_length', str(args.horizon + 200),
                        '--video_folder', str(output / 'videos')])
    metadata = {'experiment': args.experiment, 'checkpoint': str(checkpoint),
                'checkpoint_sha256': actual_hash, 'training_seed': model['training_seed'],
                'evaluation_seed': args.seed, 'requested_trials': args.num_rollouts,
                'horizon': args.horizon, 'command': command, 'cwd': str(root),
                'started_at': datetime.now().astimezone().isoformat()}
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Evaluation output:', output, flush=True)
    print(shlex.join(command), flush=True)
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    if env.get('TERM', 'dumb') == 'dumb':
        env['TERM'] = 'xterm'
    process = None
    with (output / 'evaluation.log').open('x') as log:
        try:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, errors='replace', bufsize=1)
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end='', flush=True)
            returncode = process.wait()
        except KeyboardInterrupt:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            returncode = 130
        except OSError as error:
            log.write(str(error) + '\n')
            returncode = 127
    result = summarize((output / 'evaluation.log').read_text(), args.num_rollouts)
    if returncode != 0:
        result['complete'] = False
        result['policy_success_rate'] = None
        result['validation_errors'].append(f'Evaluation process exited with code {returncode}.')
    result.update(experiment=args.experiment, checkpoint_sha256=actual_hash,
                  evaluation_seed=args.seed, horizon=args.horizon, returncode=returncode,
                  finished_at=datetime.now().astimezone().isoformat())
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Result saved:', output / 'results.json')
    if result['complete']:
        print(f"Confirmed success rate: {result['policy_success_rate']:.1%}")
    else:
        print('Evaluation incomplete or inconsistent; no final success rate reported.')
    return 0 if result['complete'] else 2


if __name__ == '__main__':
    sys.exit(main())
