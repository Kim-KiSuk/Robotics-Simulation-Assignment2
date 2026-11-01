# 동작 규칙과 데이터 병합

## 수직 파지 규칙

| 전략 옵션 | 순서 | 실험 |
|---|---|---|
| `vertical_first` | 회전 → XY → 하강 → 그립 → 상승 → 박스 이동 → 릴리즈 | `new_rule_20`, `new_rule_100` |
| `vertical_xy_first` | XY → 회전 → 하강 → 그립 → 상승 → 박스 이동 → 릴리즈 | `xy_first_20` |
| `vertical_descend_first` | 안전한 XY 대기 위치 확보 → 하강 → 회전 → XY → 그립 → 상승 → 박스 이동 → 릴리즈 | 박스 간섭 검사 포함 수집 전략 |

각 전략은 그립 후 실제 물체 상승을 확인하고 박스 위 운반 높이·입구 정렬·릴리즈·성공 판정을 거친다. 성공한 시범만 저장하고, 성공·실패 모두 장면을 리셋한다. 목표에 도달하지 못한 동작은 정체·시간 제한으로 중단한다.

`vertical_descend_first`의 안전 대기 위치는 낮은 높이에서 팔 또는 손목 카메라 하우징이 박스에 접근하는 문제 때문에 추가했다. 이 전략은 팔·그리퍼 경계와 박스 사이 간격 및 접촉 센서를 검사하고, 기준을 어긴 시도는 저장하지 않는다. 이 기능을 `vertical_first`와 `vertical_xy_first`에 적용한 것으로 간주하지 않는다.

정확한 수평 0° 파지 옵션은 도달 가능 거리 검사를 수행한다. 현재 장면에서 목표가 팔의 도달 범위를 벗어나면 이유를 표시하고 수집을 중단한다. 수평 파지 실험을 성공 수집 조건으로 보고하지 않는다.

## 새 원본 100개 수집

IsaacLab_RS와 Toy2Box 자산이 설치된 환경에서 실행한다. 경로는 설치 환경에 맞게 바꾼다. 새 출력 이름을 사용하며 기존 파일을 덮어쓰지 않는다.

```bash
conda activate lerobot-arena
cd /home/kisuk/IsaacLab_RS
REPO=/home/kisuk/IsaacLab_RS/Robotics-Simulation-Assignmnet2

./isaaclab.sh -p "$REPO/tools/collection/record_toy2box_auto.py" \
  --reference_dataset /home/kisuk/toy/toy2box_agibot.hdf5 \
  --dataset_file ./datasets/toy2box_vertical_sequence_100_repeat.hdf5 \
  --collection_strategy vertical_first \
  --num_demos 100 --max_attempts 1000 \
  --motion_style varied --target_idle_fraction 0.21 --seed 101
```

성공 저장 100개 또는 최대 시도 1,000회에 도달하면 수집이 끝난다. GUI에서는 결과 창을 유지하며 `--exit_on_finish`를 주면 종료한다. 자동 수집과 사람이 직접 조작하는 가이드 모드는 별개다. 기존 원본의 실행 방식은 보존된 `.run.json`을 따른다.

## 수동 가이드와 다중 뷰

`tools/collection/record_toy2box_auto.py`는 직접 조작 가이드를 지원한다. 전체 순서와 키 입력 횟수를 보여 주며, 위쪽·왼쪽 뷰는 조작을 돕는 화면이다. 원본 HDF5에 해당 카메라 영상을 저장한 데이터라고 해석하지 않는다. 옵션은 `--help`에서 확인한다.

## 시범 20개씩 병합

병합 자체에는 Isaac Sim이나 GPU가 필요하지 않다. Python과 `h5py`로 실행한다. 입력 데이터의 task, 관측/action 구성, 제어 간격은 먼저 맞춘다. 제공 도구는 task 이름과 action shape를 검사하며, 모든 관측 의미와 수집자 신원을 자동 검증하는 도구는 아니다.

```bash
python tools/merge_hdf5_datasets.py \
  --input_files operator_01.hdf5 operator_02.hdf5 operator_03.hdf5 \
                operator_04.hdf5 operator_05.hdf5 \
  --output_file ./data/multi_operator_100_repeat.hdf5
```

각 파일이 20개면 결과는 100개다. episode를 연속 번호로 다시 매기고 원본 파일명·원본 episode·전체 frame 수를 기록한다. 출력 파일이 이미 있으면 중단한다.

`env_args.env_name`이 빠진 파일은 task를 확인한 경우에만 `--task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0`를 명시한다. 기록된 task 이름이 서로 다르면 이 옵션으로도 통과시키지 않는다.

실제 병합본의 원본별 시범 수는 [데이터 manifest](../data/experiment_manifest.json)에 있다. 혼합 파일에 붙은 `multi operator`라는 이름만으로 독립적인 조작자 5명을 입증하지 않는다. [연구 비교에서 통제할 항목](experiments.md#다음-비교에서-맞출-조건)을 함께 확인한다.
