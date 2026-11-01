# Toy2Box 모방학습 구현

## 과업과 코드 구성

Agibot 오른팔로 트럭을 집어 박스 입구까지 옮기고 그리퍼를 연다. IsaacLab의 원래 과업 관측·성공 조건·종료 조건을 기준으로 학습과 평가를 수행한다.

| 경로 | 역할 |
| --- | --- |
| `isaaclab_project/source/isaaclab_tasks/.../place/` | Toy2Box 환경 등록·관측·종료 조건·BC 설정 |
| `isaaclab_project/source/isaaclab_assets/.../robots/agibot.py` | 로봇 초기화와 actuator 설정 |
| `isaaclab_project/scripts/imitation_learning/robomimic/` | BC 학습과 stock 정책 평가 |
| `tools/collection/` | 수집 피드백 제어·가이드·정지 구성·간격 검사 |
| `tools/merge_hdf5_datasets.py` | 원본 episode 병합과 출처 속성 보존 |
| `tools/evaluate_experiment.py` | 모델 해시 확인, 평가 실행, 로그·결과 저장 |

포함한 과업 코드는 [source manifest](../isaaclab_project/source_manifest.json)에 고정한 IsaacLab_RS 기반 코드와 파일 해시로 관리한다. Isaac Sim 엔진과 로봇·물체 USD는 별도로 설치된 자산을 사용한다.

## 정책 입력과 출력

| 상태 관측 | 차원 |
| --- | ---: |
| `eef_pos` | 3 |
| `eef_quat` | 4 |
| `gripper_pos` | 2 |
| `toy_truck_positions` | 3 |
| `toy_truck_orientations` | 4 |
| `box_positions` | 3 |
| `box_orientations` | 4 |
| 합계 | 23 |

출력 action은 상대 이동 3축·회전 3축·그리퍼 1개의 7차원이다. 팔 명령은 RMPFlow 기반 제어에 전달한다. 원본 HDF5에 추가 관절 상태가 있어도 위 정책의 입력 목록에 모두 포함되는 것은 아니다.

## 수집 순서와 리셋

New rule은 회전 → XY 접근 → 수직 하강 → 그립 → 수직 상승 → 박스 이동 → 릴리즈 순서다. Vertical은 앞부분을 XY 접근 → 회전 → 수직 하강으로 바꾼다.

수집기는 그립 후 실제 물체 상승, 운반 높이, 박스 입구 정렬과 릴리즈를 확인한다. 성공한 episode만 저장하고 성공·실패 모두 리셋한다. 정체와 시간 제한으로 끝난 시도는 성공 시범으로 저장하지 않는다.

속도 변화·작은 보정·분산 정지를 지원한다. 목표 idle은 팔 action 6개가 모두 정확히 0인 프레임의 비율로 관리하며, 정지 중 그리퍼 명령은 유지한다. 보조 top/left 뷰는 조작 화면이고 해당 RGB를 원본 데이터에 저장한 조건은 아니다. 자동 수집과 직접 조작 가이드는 별도 실행 모드다. 실제 수집 모드는 보존된 `.run.json`을 따른다.

추가 전략 `vertical_descend_first`에는 낮은 높이에서의 박스 간섭을 줄이기 위한 대기 위치와 간격·접촉 검사가 있다. 이 기능이 New rule이나 XY 우선 Vertical에 모두 적용된 것으로 간주하지 않는다. [전략별 명령과 구현 범위](collection_rules.md)

## Mimic과 BC-RNN

수집 원본을 환경에서 재생하며 annotation을 생성하고, 이를 이용해 Mimic 성공 시범을 만든 뒤 BC-RNN/GMM을 학습했다. 원본·annotation·생성 학습 시범의 개수는 구분한다. 모델별 실제 config와 학습 로그 발췌는 [학습 기록](training_status.md)에 있다.

New rule 20과 100은 같은 Mimic 출력 경로를 순차적으로 사용했다. 이전 생성 파일의 해시가 없으므로 현재 파일을 두 모델 모두의 동일한 학습 입력으로 간주하지 않는다. 각 checkpoint의 해시·당시 config·학습 로그를 따로 보존했다.

## 평가 기록

기본 평가는 stock `play.py`의 성공 판정을 사용한다. 저장 wrapper는 명령·checkpoint SHA256·전체 출력·trial별 판정을 보존한다. 최종 집계와 trial 결과가 다르거나 실행이 중단되면 성공률을 확정하지 않는다. [평가 상세](evaluation.md)

[방법](METHOD.md) · [결과](RESULTS.md) · [설치·재현](REPRODUCE.md)
