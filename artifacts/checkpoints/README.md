# Rollout 모델

각 실험에서 rollout에 사용한 **epoch 2000 가중치 하나씩** [Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/experiments-2026-11-01)에 제공한다. 모든 학습 seed는 101이다.

| 실험 | 모델 파일 | 학습 시범 |
| --- | --- | ---: |
| n100 (스크립트 테스트용) | `toy2box_baseline_n100_epoch2000.pth` | 500 |
| New rule 20 | `toy2box_new_rule_20_epoch2000.pth` | 1,000 |
| New rule 100 | `toy2box_new_rule_100_epoch2000.pth` | 1,000 |
| Multi operator | `toy2box_multi_operator_100_epoch2000.pth` | 1,000 |

기본 선택 모델 [models/final_model.pth](../../models/final_model.pth)는 New rule 100의 Release 모델과 바이트가 같다. [모델 manifest](../../models/experiment_manifest.json)에 전체 SHA256·학습 config·다운로드 URL이 있다. [선택 모델 manifest](../../models/model_manifest.json)는 기본 모델의 원본 100개 → annotation 98개 → 학습 1,000개 관계를 기록한다.

```bash
mkdir -p models/experiments
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.pth' --dir models/experiments
```

저장소 루트에서 실행한다. [평가 명령](../../docs/REPRODUCE.md#모델별-평가)을 사용하며, 중간 epoch나 Mimic HDF5는 모델 배포에 포함하지 않는다.
