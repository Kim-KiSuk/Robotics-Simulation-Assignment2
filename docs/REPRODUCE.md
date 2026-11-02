# 설치·데이터·학습 재현

## 환경과 코드 적용

Isaac Sim, Toy2Box 자산과 IsaacLab_RS가 설치된 `lerobot-arena` 환경을 사용한다. 포함 코드의 적용은 기존 파일을 백업한다.

```bash
conda activate lerobot-arena
git clone https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2.git
cd Robotics-Simulation-Assignmnet2
python tools/install_project_overlay.py --isaaclab_root "$HOME/IsaacLab_RS"
python tools/install_project_overlay.py --isaaclab_root "$HOME/IsaacLab_RS" --apply
```

이미 내려받았다면 실제 저장소 폴더로 이동한다. 아래 경로는 `/home/kisuk/IsaacLab_RS` 기준이며 설치 위치에 맞게 조정한다.

## 원본 다운로드

```bash
gh release download keyboard-study-2026-11-02 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.hdf5' --pattern SHA256SUMS --dir data
cd data
sha256sum -c SHA256SUMS
```

New rule 20개와 Multi operator 100개의 증강 전 원본이다. 학습 입력은 원본을 annotation한 뒤 생성한 Mimic 성공 시범이다. 이번 두 조건은 각 1,000개를 사용한다. 공개 파일의 내용과 해시는 [데이터 기록](../results/keyboard_study_20261102.json)에 있다.

## 시드 101 학습

해당 Mimic 파일이 로컬에 준비된 상태에서 실행한다.

```bash
cd /home/kisuk/IsaacLab_RS
REPO=/home/kisuk/IsaacLab_RS/Robotics-Simulation-Assignmnet2
./isaaclab.sh -p "$REPO/isaaclab_project/scripts/imitation_learning/robomimic/train.py" \
  --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 \
  --algo bc \
  --config "$REPO/configs/keyboard/bc_rnn_seed101.json" \
  --dataset ./datasets/toy2box_agibot_mimic_new_rule_keyboard_100.hdf5 \
  --name new_rule_keyboard_seed101
```

## 시드 100 비교 학습

별도 터미널에서 실행할 수 있다. 두 프로세스가 같은 GPU와 시스템 메모리를 함께 사용하므로 여유가 부족하면 순서대로 실행한다.

```bash
cd /home/kisuk/IsaacLab_RS
REPO=/home/kisuk/IsaacLab_RS/Robotics-Simulation-Assignmnet2
./isaaclab.sh -p "$REPO/isaaclab_project/scripts/imitation_learning/robomimic/train.py" \
  --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 \
  --algo bc \
  --config "$REPO/configs/keyboard/bc_rnn_seed100.json" \
  --dataset ./datasets/toy2box_agibot_mimic_new_rule_keyboard_100.hdf5 \
  --name new_rule_keyboard_seed100
```

두 명령의 데이터·모델 설정은 같고 학습 시드와 저장 이름을 다르게 지정한다. 실제 시드는 JSON의 `train.seed`다. `--name`에 숫자를 적는 것만으로 시드가 바뀌지 않는다. 저장소에 포함한 `bc_rnn_low_dim_2.json`도 알고리즘 `bc`, 시드 `100`이다.

Multi operator 학습은 데이터 경로를 `./datasets/toy2box_agibot_mimic_multi_operator_keyboard_100.hdf5`로 바꾸고 조건·시드별 이름을 분리한다. 이 명령을 제공한 것만으로 해당 학습이 실행·완료됐다는 의미는 아니다.

## 평가

이번 조건의 rollout·영상·성공률은 평가 대기다. 평가 모델이 정해지면 같은 평가 seed·100회·800 step으로 실행하고 trial별 성공 판정, checkpoint 해시와 로그를 보존한다. 평가 전 checkpoint를 최종 모델로 지정하지 않는다.

[준비 현황](RESULTS.md) · [평가 로그 형식](evaluation.md) · [이전 조건 재현](reproduction.md)
