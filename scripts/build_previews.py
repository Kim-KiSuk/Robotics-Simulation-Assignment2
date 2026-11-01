"""Extract fixed, real-time video excerpts for the repository README."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ['new_rule_20', 'new_rule_100', 'multi_operator_100']


def main():
    models = {r['id']: r for r in json.loads((ROOT / 'models/experiment_manifest.json').read_text())['models']}
    output = ROOT / 'artifacts/media'
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for ident in EXPERIMENTS:
        source = ROOT / 'videos/experiments' / ident / 'rollout-episode-0.mp4'
        cap = cv2.VideoCapture(str(source))
        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or source_fps <= 0:
            raise ValueError(f'Cannot open {source}')
        stride = round(source_fps / 10)
        if stride < 1 or abs(source_fps / stride - 10) > 1e-6:
            raise ValueError('Expected a source FPS that permits exact 10-FPS sampling.')
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(source_fps * 8))
        frames = []
        for index in range(round(source_fps * 6)):
            ok, bgr = cap.read()
            if not ok:
                raise ValueError(f'Video ends before the fixed 8–14 second excerpt: {source}')
            if index % stride == 0:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                height = round(rgb.shape[0] * 480 / rgb.shape[1])
                frames.append(Image.fromarray(cv2.resize(rgb, (480, height), interpolation=cv2.INTER_AREA)))
        cap.release()
        gif = output / f'{ident}_preview.gif'
        poster = output / f'{ident}_poster.png'
        frames[0].save(poster)
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=100,
                       loop=0, disposal=2, optimize=True)
        with Image.open(gif) as image:
            duration = 0
            for index in range(image.n_frames):
                image.seek(index)
                duration += image.info['duration']
            assert duration == 6000, (gif, duration)
        records.append({
            'experiment': ident,
            'trial': 0,
            'source_video': str(source.relative_to(ROOT)),
            'source_video_sha256': sha256(source.read_bytes()).hexdigest(),
            'preview': str(gif.relative_to(ROOT)),
            'preview_sha256': sha256(gif.read_bytes()).hexdigest(),
            'poster': str(poster.relative_to(ROOT)),
            'clip_start_seconds': 8,
            'clip_duration_seconds': 6,
            'preview_fps': 10,
            'playback_speed': 1,
            'source_fps': source_fps,
            'checkpoint_sha256': models[ident]['checkpoint_sha256'],
            'checkpoint_association': 'execution history; source MP4 has no embedded checkpoint digest',
            'selection': 'trial 0 and fixed 8–14 second interval; independent of success outcome',
            'policy_success': None,
        })
    (output / 'manifest.json').write_text(json.dumps({'previews': records}, ensure_ascii=False, indent=2) + '\n')
    print('Built three 6-second, real-time GIF previews and their provenance manifest.')


if __name__ == '__main__':
    main()
