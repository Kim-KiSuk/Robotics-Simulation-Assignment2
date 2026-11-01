# 공개 데이터

[Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/collection-2026-10-28)에서 두 원본을 제공한다.

| 실험 | 파일 |
|---|---|
| Dataset A | `toy2box_dataset_a.hdf5` |
| Dataset B | `toy2box_dataset_b.hdf5` |

```bash
python tools/download_data.py
```

[manifest.json](manifest.json)은 실험 이름, 공개 파일명, 수집 원본 파일명, 크기, SHA256과 다운로드 URL을 담는다. 도구는 다운로드 후 원본 해시를 확인한다. 이름을 바꾸어도 데이터 바이트는 변경하지 않았다.

annotation·Mimic 관련 파일은 [통계·연결 관계](../docs/data_collection.md)만 보관한다. 이 파일들은 기본 다운로드에 포함되지 않는다.

## 동작 규칙·혼합 수집 실험 원본

[실험 Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/experiments-2026-11-01)에 아래 원본을 별도로 제공한다. `tools/download_data.py`의 기존 기본 다운로드는 Dataset A/B만 받는다.

| 실험 ID | 파일 | 시범 수 |
|---|---|---:|
| `new_rule_20` | `toy2box_new_rule_20.hdf5` | 20 |
| `new_rule_100` | `toy2box_new_rule_100.hdf5` | 100 |
| `multi_operator_100` | `toy2box_multi_operator_100.hdf5` | 100 |
| `xy_first_20` | `toy2box_xy_first_20.hdf5` | 20 |

```bash
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.hdf5' --pattern SHA256SUMS --dir data
cd data
sha256sum --ignore-missing -c SHA256SUMS
```

원본 파일의 바이트를 그대로 보존했으며 공개 파일명만 정리했다. [manifest](experiment_manifest.json)에는 원본 파일명, 시범 수, idle, SHA256, 다운로드 URL, 병합한 원본별 개수가 있다. annotation·Mimic 전체 파일은 이 Release에 포함하지 않는다. 실험 모델은 [모델 다운로드 안내](../docs/evaluation.md)에 따라 받는다.
