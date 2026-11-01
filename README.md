# Agibot Toy2Box — Robotics Simulation Assignment 2

**연구 질문:** 시범의 동작 순서와 수집 데이터 구성이 Agibot Toy2Box 모방학습 정책의 성능에 어떤 영향을 주는가?

## 실험 비교

| 실험 | 원본 시범 | annotation | Mimic 학습 시범 | 평균 원본 길이 | 원본 idle 평균 |
|---|---:|---:|---:|---:|---:|
| 기준 수집 `baseline_n100` | 100 | 99 | 500 | 14.61초 | 0.70% |
| 수직 파지 순서 통일 `new_rule_20` | 20 | 19 | 1,000 | 32.81초 | 20.23% |
| 수직 파지 순서 통일 `new_rule_100` | 100 | 98 | 1,000 | 32.20초 | 20.08% |
| 혼합 수집 `multi_operator_100` | 100 | 93 | 1,000 | 34.16초 | 27.41% |

`new rule`은 **회전 → XY 이동 → 수직 하강 → 그립 → 수직 상승 → 박스 이동 → 릴리즈** 순서다. `new_rule_20`과 `new_rule_100`을 별도 실험으로 관리한다. 학습은 BC-RNN/GMM, seed 101, epoch 2000이며, 정책 평가 명령의 조건은 seed 42, 100회, horizon 800이다.

**정확한 정책 성공률은 평가 결과 로그 확인 전까지 미확정이다.** 영상 100개 중 800프레임 미만인 파일은 `new_rule_20` 56개, `new_rule_100` 68개, `multi_operator_100` 32개지만, 조기 종료에는 실패도 포함될 수 있어 성공 횟수로 사용하지 않는다. 기존 공용 영상 폴더는 다른 모델 평가에도 재사용되어 n100의 결과로 연결하지 않는다.

- [실험 구성·비교·해석](docs/experiments.md) · [원본/학습 데이터와 체크포인트 근거](reports/experiment_inventory.json)
- 추가 실험 원본·비교 모델은 [데이터 manifest](data/experiment_manifest.json)와 [모델 manifest](models/experiment_manifest.json)로 구성·해시를 제공한다. 공개 가중치는 `models/final_model.pth` 한 개다.
- [동작 규칙·수집 및 병합 방법](docs/collection_rules.md) · [평가 실행과 결과 저장](docs/evaluation.md)
- [실험별 정책 영상·시범 재생 영상](docs/videos.md#실험별-영상)

학습 입력 파일명이 같더라도 동일한 데이터라고 간주하지 않는다. `new_rule_20` 학습 때 사용한 Mimic 경로가 `new_rule_100` 생성에 재사용되어, 모델별 config·학습 로그 발췌·체크포인트 해시를 따로 보관한다.


## 제출 파일

| 제출 항목 | 위치 | 상태 |
|---|---|---|
| 최종 모델 1개 | [models/final_model.pth](models/final_model.pth) | BC-RNN/GMM · epoch 2000 · 학습 seed 101 |
| 평가 명령어 | [submission/evaluate.txt](submission/evaluate.txt) | 검증 seed 42, rollout 100회, horizon 800 |
| 제출 파일 확인 | [submission/checklist.md](submission/checklist.md) | 실행 파일·모델·명령어 확인 |


## 공개 기준 데이터

| 실험 이름 | 시범 수 | 평균 길이 | idle 평균 | 용도 |
|---|---:|---:|---:|---|
| **Dataset A** | 100 | 14.61초 | 0.70% | 수집·증강 참고 기준 |
| **Dataset B** | 20 | 21.02초 | 19.79% | 동작 시간 구성 비교용 |

A/B는 데이터 세트 식별자이며 시범 개수나 소요 시간을 뜻하지 않는다. 수집 방식과 실행 이력은 [수집 기록](docs/data_collection.md)에 정리했다. idle은 팔의 이동·회전 명령 6개가 모두 정확히 0인 프레임의 비율이며, 그리퍼 값은 제외한다. 수집 통계는 BC 정책 평가 성공률과 구분한다.

- 공개 데이터: [Dataset A / Dataset B HDF5](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/collection-2026-10-28)
- [수집 방법·전체 통계](docs/data_collection.md) · [파일명 대응·SHA256](data/manifest.json)
- [최종 모델의 학습 이력](docs/training_status.md) · [학습 config](configs/final_train_config.json)

## 영상

[![Dataset A과 Dataset B의 시범 재생](videos/previews/contact_sheet.jpg)](docs/videos.md)

| 데이터 | 실제 시범 재생 영상 |
|---|---|
| Dataset A | [demo_0](videos/dataset_a/demo_0.mp4) · [demo_49](videos/dataset_a/demo_49.mp4) · [demo_99](videos/dataset_a/demo_99.mp4) |
| Dataset B | [demo_0](videos/dataset_b/demo_0.mp4) · [demo_9](videos/dataset_b/demo_9.mp4) · [demo_19](videos/dataset_b/demo_19.mp4) |

위 6개는 HDF5 초기 상태와 저장 action을 실제 시뮬레이터에서 재생한 영상이다. 선택한 6개 모두 기존 성공 조건을 10 step 연속 충족했다. 학습된 정책의 독립 평가 영상과는 구분한다. [영상 설명·검사 결과](docs/videos.md)를 참고한다.

## 실행

기존 IsaacLab_RS 환경에서 다음 명령을 실행한다. `REPO`는 이 저장소의 절대 경로다.

```bash
conda activate lerobot-arena
cd /home/kisuk/IsaacLab_RS
REPO=/home/kisuk/IsaacLab_RS/Robotics-Simulation-Assignmnet2

./isaaclab.sh -p "$REPO/isaaclab_project/scripts/imitation_learning/robomimic/play.py"   --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0   --checkpoint "$REPO/models/final_model.pth"   --num_rollouts 100 --horizon 800 --seed 42 --headless
```

새 환경에는 [설치·재현 방법](docs/reproduction.md)에 따라 고정한 IsaacLab_RS 기반 코드 위에 `isaaclab_project/`를 적용한다. 로봇·물체 USD와 Isaac Sim 자체는 별도 설치 자산이다.

## 평가 상태

제출용 선택 모델은 `models/final_model.pth` 한 개다. 비교 모델 가중치는 로컬에 보관하고 구성·학습 이력만 제공한다. [부분 실행 기록](submission/model_smoke_check.json)은 100회 정식 평가 결과가 아니다. 실험 모델의 정책 성공률, 학습 seed 101·111 비교, 실패 단계 분류와 단일 요인 통제 실험은 [실험 보고서](docs/experiments.md)에 확인 범위를 구분했다.

## 폴더

```text
isaaclab_project/       과업 환경·로봇·RMPFlow·BC 학습 및 평가 코드
models/                최종 가중치 1개와 SHA256 manifest
submission/            평가 명령어, 제출 기준, 발표 PPT 초안
configs/               선택 모델과 참고 학습 설정
reports/               episode CSV, 수집 로그, 데이터 연결·영상 검사
videos/                Dataset A·Dataset B 재생 영상, 정책 참고 영상
tools/                 다운로드·분석·재생·설치 도구
```

검증: `python -m pytest -q tools/collection/test tools/test`.
[외부 코드 고지](THIRD_PARTY_NOTICES.md)를 참고한다.
