# 선택 모델과 학습 기록

## 최종 모델

| 항목 | 값 |
|---|---|
| 파일 | `models/final_model.pth` |
| 데이터 계열 | 수집 원본 100개 → annotation 98개 → Mimic 성공 생성 1,000개 |
| source checkpoint | `20261101015656/models/model_epoch_2000.pth` |
| 선택 기준 | 사용자 지정, 고정 epoch 2000 |
| 학습 seed | 101 |
| 정책 | BC-RNN, LSTM hidden 400·2 layers, GMM 5 modes |
| batch / sequence length | 100 / 10 |
| optimizer | Adam, 학습률 0.001 |
| epoch당 학습 step 설정 | 100 |
| 배포 구성 | 저장소 기본 모델 1개, Release에 5개 실험의 최종 epoch 모델 각각 1개 |

모델 내부 config가 `toy2box_agibot_mimic_new_rule_1000.hdf5`를 학습 입력으로 사용했음을 확인했다. 학습 시범은 1,000개다. 원본 HDF5 100개와 증강 학습 데이터 1,000개를 구분한다. [모델 manifest](../models/model_manifest.json)와 [학습 config](../configs/final_train_config.json)를 제공한다.

기본 선택 모델은 `new_rule_100`이다. Release의 동일 실험 모델과 SHA256이 같다. 이전 n20 모델의 선택 정보와 7회 부분 실행은 [이력 폴더](../reports/history)에 보관하며 현재 선택 모델의 평가 결과로 사용하지 않는다.

## 실제 입력

```text
eef_pos                  3
eef_quat                 4
gripper_pos              2
toy_truck_positions      3
toy_truck_orientations   4
box_positions            3
box_orientations         4
총 입력                 23차원
```

HDF5 전체 관측과 실제 policy 입력을 구분한다. 저장된 관절 상태는 이 config의 입력 목록에 없다.

## 평가와 분석

선택 모델의 CPU 로드·내부 config·파일 해시를 확인했다. 기존 rollout 명령 이력과 영상 100개를 [근거 기록](../submission/model_smoke_check.json)으로 연결했다. 정확한 성공 여부 출력은 확보되지 않아 정식 100회 성공률이나 학습 seed 2개의 평균·표준편차로 사용하지 않는다. 이번 배포 수정에서 시뮬레이터 재평가는 실행하지 않았다.

[평가 명령어](../submission/evaluate.txt)는 `--num_rollouts 100 --horizon 800 --seed 42`를 따른다. 이 검증 seed와 조교의 비공개 평가 seed를 구분한다.

추가 확인 항목은 학습 seed 111, 접근·파지·운반·배치 실패 분류, 진단한 원인 하나에 대한 통제 실험이다. 수집기의 성공률과 정책 평가 성공률을 혼동하지 않는다.

## 비교 실험 모델

아래 5개 실험은 모두 seed 101, epoch 2000이며, 각각 수집 원본 HDF5와 rollout 모델을 한 쌍씩 Release에 제공한다. `new_rule_100`은 기본 선택 모델과 같은 가중치다.

| 실험 ID | 학습 run | 학습 시범 수 |
|---|---|---:|
| `baseline_n100` | `20261027100809` | 500 |
| `new_rule_20` | `20261029111434` | 1,000 |
| `xy_first_20` | `20261029203527` | 1,000 |
| `multi_operator_100` | `20261031151706` | 1,000 |
| `new_rule_100` | `20261101015656` | 1,000 |

`new_rule_20`과 `new_rule_100`의 config에는 같은 HDF5 경로가 기록돼 있지만 생성 원본과 학습 실행은 다르다. 당시 학습 입력의 해시를 기록하지 않았으므로 현재 파일을 두 모델의 동일한 입력이었다고 간주하지 않는다.

[실험 구성과 확인 범위](experiments.md) · [체크포인트 manifest](../models/experiment_manifest.json) · [평가·결과 저장](evaluation.md)
