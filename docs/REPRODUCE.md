# 설치·다운로드·평가 재현

## 실행 환경

Isaac Sim, Toy2Box 로봇·물체 자산과 IsaacLab_RS가 설치된 `lerobot-arena` 환경을 사용한다. 이 저장소는 과업 코드·수집 도구·모델·배포 자료를 포함한다. Isaac Sim 엔진과 전체 IsaacLab 설치를 압축해 제공하는 저장소는 아니다.

기반 commit과 과업 코드 해시는 [source manifest](../isaaclab_project/source_manifest.json), 확인한 Python 패키지 버전은 [software versions](../configs/software_versions.json)에 있다.

## 처음 실행

```bash
conda activate lerobot-arena
git clone https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2.git
cd Robotics-Simulation-Assignmnet2

python tools/install_project_overlay.py \
  --isaaclab_root "$HOME/IsaacLab_RS"
python tools/install_project_overlay.py \
  --isaaclab_root "$HOME/IsaacLab_RS" --apply

python tools/evaluate_experiment.py \
  --isaaclab_root "$HOME/IsaacLab_RS" \
  --experiment new_rule_100 \
  --num_rollouts 100 --horizon 800 --seed 42 \
  --output_root ./results/evaluations \
  --headless --video
```

첫 overlay 명령은 파일 검사와 적용 계획만 보여 준다. `--apply`는 변경할 원본을 백업하고 포함 코드를 복사한다. 이미 clone했거나 ZIP을 푼 경우 저장소 폴더로 이동해 실행한다. 설치 경로가 다르면 `--isaaclab_root`를 바꾼다.

기본 모델은 `models/final_model.pth`이며 별도 다운로드 없이 들어 있다. 파일 해시는 New rule 100의 Release 모델과 같다. 화면을 보려면 `--headless`를 뺀다.

## 원본 HDF5와 비교 모델 다운로드

GitHub CLI가 있으면 저장소 루트에서 실행한다. 없는 경우 [Release](https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2/releases/tag/experiments-2026-11-01) 화면에서 같은 파일을 받는다.

```bash
mkdir -p data models/experiments
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.hdf5' --pattern SHA256SUMS --dir data
gh release download experiments-2026-11-01 \
  --repo Kim-KiSuk/Robotics-Simulation-Assignmnet2 \
  --pattern '*.pth' --dir models/experiments
```

원본은 n100 100개, New rule 20개·100개, Vertical 20개, Multi operator 100개다. annotation·Mimic 파일은 포함하지 않는다. [데이터 안내](../artifacts/datasets/README.md) · [모델 안내](../artifacts/checkpoints/README.md)

## 모델별 평가

같은 평가 seed·horizon·rollout 수를 사용하고 순서대로 완료한다.

```bash
python tools/evaluate_experiment.py \
  --isaaclab_root "$HOME/IsaacLab_RS" \
  --experiment new_rule_20 --num_rollouts 100 --horizon 800 --seed 42 \
  --output_root ./results/evaluations --headless
```

`--experiment`는 `baseline_n100`, `new_rule_20`, `new_rule_100`, `xy_first_20`, `multi_operator_100` 중 하나다. `xy_first_20`이 문서의 Vertical이다. 보유한 checkpoint를 지정하려면 `--checkpoint /absolute/path/model_epoch_2000.pth`를 추가한다. 해당 실험의 해시와 일치해야 한다.

`results/evaluations/<실험ID>_<시각>/`에 `metadata.json`, `evaluation.log`, `results.json`과 선택한 경우 영상이 저장된다. `complete: true`인 검증 결과만 최종 성공률로 사용한다. 기존 로그 분석과 중단 처리 상세는 [평가 도구 안내](evaluation.md)에 있다.

## 수집·annotation·Mimic·학습

[동작 규칙별 수집 명령과 원본 병합](collection_rules.md)을 따른다. 병합에는 Python과 h5py만 필요하며, 수집·annotation·생성에는 시뮬레이터가 필요하다.

공개 원본을 그대로 학습한 모델이 아니라 annotation 후 Mimic 성공 시범으로 학습한 모델이다. New rule 100은 100 → 98 → 1,000개를 사용했다. 학습 명령과 실제 config는 [기존 재현 상세](reproduction.md#학습-코드)에 있다. 재생성한 Mimic이 과거 학습 파일과 바이트 단위로 같다고 보장하지 않는다.

## 그림·영상·배포 검사

```bash
python scripts/build_figures.py
python scripts/build_previews.py
python scripts/verify_publication.py
```

그림은 manifest, GIF는 저장소의 실제 MP4를 사용한다. 모델 rollout을 다시 실행하거나 새 성공률을 생성하는 명령이 아니다. 상세 제출용 명령은 [evaluation_command.txt](../submission/evaluation_command.txt), 이미 준비된 환경의 평가 명령은 [evaluation_only.txt](../submission/evaluation_only.txt)에 있다.
