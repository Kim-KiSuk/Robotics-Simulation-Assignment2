"""Build experiment tables and original-data figures from the published manifests."""

import csv
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ORDER = ['baseline_n100', 'new_rule_20', 'new_rule_100', 'multi_operator_100']
LABELS = ['Script test\n(n100)', 'New rule 20', 'New rule 100', 'Multi 100']


def main():
    data = {r['id']: r for r in json.loads((ROOT / 'data/experiment_manifest.json').read_text())['datasets']}
    models = {r['id']: r for r in json.loads((ROOT / 'models/experiment_manifest.json').read_text())['models']}
    replays = {r['id']: r for r in json.loads((ROOT / 'reports/replay_inventory.json').read_text())['datasets']}
    rows = []
    for ident in ORDER:
        dataset, model, replay = data[ident], models[ident], replays.get(ident, {})
        rows.append({
            'experiment': ident,
            'role': model['role'],
            'display_name': model['display_name'],
            'operator_comparison_group': model['operator_comparison_group'],
            'source_composition': '; '.join(model.get('display_sources', [])),
            'original_demos': dataset['episodes'],
            'annotated_demos': model['annotation_episodes'],
            'training_demos': model['training_episodes'],
            'mean_original_seconds': round(dataset['mean_seconds'], 4),
            'mean_original_idle_percent': round(dataset['mean_episode_idle_fraction'] * 100, 4),
            'training_seed': model['training_seed'],
            'checkpoint_epoch': model['epoch'],
            'evaluation_seed': 42,
            'requested_evaluation_rollouts': 100,
            'evaluation_horizon': 800,
            'confirmed_policy_success_rate': model['policy_success_rate'],
            'recorded_action_replay_successes': replay.get('success_10_consecutive_steps'),
            'recorded_action_replay_episodes': replay.get('replayed_episodes'),
        })
    result_dir = ROOT / 'results'
    result_dir.mkdir(exist_ok=True)
    with (result_dir / 'experiment_summary.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    (result_dir / 'experiment_summary.json').write_text(json.dumps({
        'sources': ['data/experiment_manifest.json', 'models/experiment_manifest.json', 'reports/replay_inventory.json'],
        'policy_success_status': 'unconfirmed_until_complete_evaluation_log_is_available',
        'rows': rows,
    }, ensure_ascii=False, indent=2) + '\n')

    colors = ['#8a99ae', '#5376aa', '#168a83', '#c18b4d']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.titleweight': 'bold'})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7), constrained_layout=True)
    panels = [('Original demonstrations', 'Episodes', 'original_demos'),
              ('Mean episode length', 'Seconds', 'mean_original_seconds'),
              ('Mean idle fraction', 'Percent of control steps', 'mean_original_idle_percent')]
    for ax, (title, ylabel, key) in zip(axes, panels):
        values = [row[key] for row in rows]
        bars = ax.bar(np.arange(len(rows)), values, color=colors, width=.65)
        ax.set_title(title, pad=12)
        ax.set_ylabel(ylabel)
        ax.set_xticks(np.arange(len(rows)), LABELS, rotation=28, ha='right')
        ax.set_ylim(0, max(values) * 1.22)
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#e6eaf0', linewidth=.8)
        for bar, value in zip(bars, values):
            label = str(int(value)) if key == 'original_demos' else str(
                Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * .025,
                    label, ha='center', va='bottom', fontsize=10)
    fig.suptitle('Toy2Box: characteristics of the collected demonstrations', fontsize=15, fontweight='bold')
    dest = ROOT / 'artifacts/figures'
    dest.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest / 'dataset_comparison.png', dpi=170, facecolor='white')
    svg = dest / 'dataset_comparison.svg'
    fig.savefig(svg, facecolor='white')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)
    print('Built results/experiment_summary.{csv,json} and artifacts/figures/dataset_comparison.{png,svg}')


if __name__ == '__main__':
    main()
