# 정책 평가와 결과 저장

## 실험 모델 준비

체크포인트의 실험 ID·SHA256·학습 조건은 [모델 manifest](../models/experiment_manifest.json)에 있다. 모델 경로 이름은 학습 당시 로그 폴더가 바뀌더라도 실험 ID와 해시로 구분한다.

기본 선택 모델은 new rule 100개 실험의 `models/final_model.pth`다. 연구 조건 3종과 n100은 각각 rollout에 사용한 epoch 2000 가중치 하나를 [Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/experiments-2026-11-01)로 제공한다. 중간 epoch 가중치는 포함하지 않는다.

저장소 루트에서 다음을 실행한다. GitHub CLI가 없으면 Release 화면에서 같은 파일을 내려받아 `models/experiments/`에 넣는다.

```bash
mkdir -p models/experiments
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.pth' --dir models/experiments
```

`new_rule_100`은 저장소의 `models/final_model.pth`를 기본으로 사용한다. 다른 실험은 내려받은 파일을 기본으로 사용한다. 설치된 로컬 checkpoint를 사용할 때는 `--checkpoint`를 지정한다.

## 모델 하나당 100회 평가

IsaacLab_RS와 로봇·물체 자산이 설치된 환경에서 실행한다. 같은 GPU에서 동시에 여러 평가를 실행하지 않고 순서대로 완료한다.

```bash
conda activate lerobot-arena
cd /path/to/Robotics-Simulation-Assignmnet2

python tools/evaluate_experiment.py \
  --isaaclab_root /home/kisuk/IsaacLab_RS \
  --experiment new_rule_20 --headless

python tools/evaluate_experiment.py \
  --isaaclab_root /home/kisuk/IsaacLab_RS \
  --experiment multi_operator_100 --headless

python tools/evaluate_experiment.py \
  --isaaclab_root /home/kisuk/IsaacLab_RS \
  --experiment baseline_n100 --headless

python tools/evaluate_experiment.py \
  --isaaclab_root /home/kisuk/IsaacLab_RS \
  --experiment new_rule_100 --headless

```

기본값은 평가 seed 42, rollout 100회, horizon 800이다. `--headless`를 빼면 화면을 보며 평가한다. `--video`를 추가하면 해당 실행 폴더 안에 영상을 저장한다. 설치된 로컬 checkpoint를 쓰려면 `--checkpoint /absolute/path/model_epoch_2000.pth`를 추가한다. 선택한 실험 manifest와 해시가 일치해야 한다.

실행마다 `reports/evaluations/<실험ID>_<실행시각>/`을 새로 만든다.

| 파일 | 내용 |
|---|---|
| `metadata.json` | 명령어, checkpoint SHA256, 학습·평가 seed, horizon |
| `evaluation.log` | `play.py`의 전체 출력 |
| `results.json` | rollout별 성공 여부, 완료 수, 성공 수와 검증한 성공률 |

stock `play.py`의 성공 판정과 종료 조건을 사용한다. wrapper는 출력 저장과 결과 검증을 담당하며 평가 규칙을 바꾸지 않는다. 중단됐거나 최종 요약과 rollout별 결과가 맞지 않으면 `complete: false`, `policy_success_rate: null`을 기록한다. 영상 길이로 성공을 추정하지 않는다.

## 기존 로그만 분석

이미 `tee` 등으로 저장한 출력이 있으면 시뮬레이터를 다시 켜지 않고 분석할 수 있다.

```bash
python tools/summarize_policy_evaluation.py /path/to/evaluation.log \
  --expected_trials 100 --output /path/to/new_results.json
```

`policy_success_rate`가 `0.48`이고 `complete`가 `true`이면 100회 중 48회 성공이다. 성공률은 모델 하나의 평가 결과이며, 다른 학습 seed와 평균을 낸 값으로 표기하지 않는다.
