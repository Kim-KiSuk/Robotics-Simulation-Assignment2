# 원본 데이터 다운로드

[Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/experiments-2026-11-01)에 증강 전 원본을 제공한다.

| 조건 | 파일 | 원본 시범 |
| --- | --- | ---: |
| New rule 20 | `toy2box_new_rule_20.hdf5` | 20 |
| New rule 100 | `toy2box_new_rule_100.hdf5` | 100 |
| Multi operator | `toy2box_multi_operator_100.hdf5` | 100 |
| n100 (스크립트 테스트용) | `toy2box_baseline_n100.hdf5` | 100 |

다수 조건은 new_rule, vertical, 팀원 1, 팀원 2, 조교님 데이터를 각각 20개씩 혼합한 총 100개다.

```bash
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.hdf5' --pattern SHA256SUMS --dir data
cd data
sha256sum --ignore-missing -c SHA256SUMS
```

[데이터 manifest](experiment_manifest.json)에는 시범 수·통계·SHA256·다운로드 URL이 있다. 공개 파일명만 정리했으며 원본 바이트는 유지했다. annotation·Mimic HDF5는 배포에 포함하지 않는다.

[데이터 구성](../docs/data_collection.md) · [모델 다운로드·평가](../docs/evaluation.md)
