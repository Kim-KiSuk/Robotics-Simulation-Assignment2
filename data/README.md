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

아래 추가 원본은 로컬에 보관하고 시범 수·통계·SHA256만 제공한다. `tools/download_data.py`의 기본 다운로드는 이미 공개된 Dataset A/B만 받는다.

| 실험 ID | 원본 파일명 | 시범 수 |
|---|---|---:|
| `new_rule_20` | `toy2box_vertical_sequence_20.hdf5` | 20 |
| `new_rule_100` | `toy2box_vertical_sequence_100.hdf5` | 100 |
| `multi_operator_100` | `multi_operator_100.hdf5` | 100 |
| `xy_first_20` | `toy2box_vertical_xy_rotate_z_20.hdf5` | 20 |

[manifest](experiment_manifest.json)에는 원본 경로, 시범 수, idle, SHA256, 보관 상태와 병합한 원본별 개수가 있다. 추가 원본·annotation·Mimic HDF5는 저장소에 포함하지 않는다. 보유한 실험 모델의 평가는 [평가 안내](../docs/evaluation.md)에 따른다.
