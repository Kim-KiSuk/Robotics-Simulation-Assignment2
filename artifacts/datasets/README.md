# 수집 원본 HDF5

다섯 실험의 증강 전 원본을 [Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/experiments-2026-11-01)에서 제공한다.

| 실험 | 파일 | 수집 원본 |
| --- | --- | ---: |
| n100 | `toy2box_baseline_n100.hdf5` | 100 |
| New rule 20 | `toy2box_new_rule_20.hdf5` | 20 |
| New rule 100 | `toy2box_new_rule_100.hdf5` | 100 |
| Vertical | `toy2box_xy_first_20.hdf5` | 20 |
| Multi operator | `toy2box_multi_operator_100.hdf5` | 100 |

원본 파일의 바이트는 보존하고 공개 파일명만 정리했다. [데이터 manifest](../../data/experiment_manifest.json)에 원본 경로·시범 수·idle·SHA256·다운로드 URL이 있다. [원본/모델 대응](../../reports/original_rollout_pairs.json)으로 각 원본에 연결된 rollout 모델을 확인한다.

```bash
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.hdf5' --pattern SHA256SUMS --dir data
```

저장소 루트에서 실행한다. annotation·Mimic 학습 시범은 이 HDF5들에 포함돼 있지 않다. 상태·action 원본을 실제 영상으로 재생하는 방법은 [재현 안내](../../docs/REPRODUCE.md)에 있다.
