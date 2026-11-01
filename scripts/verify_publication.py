"""Check local publication links, selected weights, result tables, and real-video previews."""

from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import unquote

import cv2
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def main():
    links = 0
    report_path = ROOT / 'results/publication_validation.json'
    for markdown in ROOT.rglob('*.md'):
        if '.git' in markdown.parts:
            continue
        for target in re.findall(r'\]\(([^)]+)\)', markdown.read_text()):
            if target.startswith(('https:', 'http:', 'mailto:', '#')):
                continue
            path = unquote(target.split('#', 1)[0].split(' "', 1)[0].strip('<>'))
            if path:
                resolved = (markdown.parent / path).resolve()
                assert resolved == report_path or resolved.exists(), (markdown.relative_to(ROOT), target)
                links += 1
    for path in ROOT.rglob('*.json'):
        if '.git' not in path.parts:
            json.loads(path.read_text())
    final = json.loads((ROOT / 'models/model_manifest.json').read_text())
    assert sha256((ROOT / final['model_file']).read_bytes()).hexdigest() == final['sha256']
    rows = json.loads((ROOT / 'results/experiment_summary.json').read_text())['rows']
    originals = {row['id']: row for row in json.loads((ROOT / 'data/experiment_manifest.json').read_text())['datasets']}
    models = {row['id']: row for row in json.loads((ROOT / 'models/experiment_manifest.json').read_text())['models']}
    assert len(rows) == 4
    for row in rows:
        assert row['original_demos'] == originals[row['experiment']]['episodes']
        assert row['confirmed_policy_success_rate'] == models[row['experiment']]['policy_success_rate']
        assert row['training_demos'] == models[row['experiment']]['training_episodes']
        assert row['role'] == models[row['experiment']]['role']
    previews = json.loads((ROOT / 'artifacts/media/manifest.json').read_text())['previews']
    for row in previews:
        source, gif = ROOT / row['source_video'], ROOT / row['preview']
        assert sha256(source.read_bytes()).hexdigest() == row['source_video_sha256']
        assert sha256(gif.read_bytes()).hexdigest() == row['preview_sha256']
        with Image.open(gif) as image:
            milliseconds = 0
            for index in range(image.n_frames):
                image.seek(index)
                milliseconds += image.info['duration']
            assert milliseconds == 6000
            assert image.width == 480 and image.height == 270
        cap = cv2.VideoCapture(str(source))
        assert cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT) >= cap.get(cv2.CAP_PROP_FPS) * 14
        cap.release()
    overlay = json.loads((ROOT / 'isaaclab_project/source_manifest.json').read_text())
    for row in overlay['files']:
        assert sha256((ROOT / 'isaaclab_project' / row['path']).read_bytes()).hexdigest() == row['sha256']
    assert (ROOT / 'submission/evaluation_command.txt').read_bytes() == (ROOT / 'submission/evaluate.txt').read_bytes()
    result = {'status': 'passed', 'relative_markdown_links': links, 'experiment_rows': len(rows),
              'real_time_previews': len(previews), 'preview_duration_seconds': 6,
              'selected_checkpoint_sha256': final['sha256'], 'overlay_files_verified': len(overlay['files']),
              'selected_checkpoint_matches_manifest': True, 'policy_reevaluation_performed': False}
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
