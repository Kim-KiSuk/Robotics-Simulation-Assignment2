# Toy2Box 모방학습 구현

## 과업

Agibot 오른팔로 트럭을 집어 박스에 놓는다. Task는 `Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0`이며, 원래 과업의 관측·성공 조건·종료 조건을 기준으로 한다.

## 정책 입력과 출력

| 관측 | 차원 |
| --- | ---: |
| EE 위치 / 자세 | 3 / 4 |
| 그리퍼 상태 | 2 |
| 트럭 위치 / 자세 | 3 / 4 |
| 박스 위치 / 자세 | 3 / 4 |
| 합계 | 23 |

출력은 상대 이동 3축·회전 3축·그리퍼 1개인 7차원이다. 팔 명령은 RMPFlow에 전달한다. HDF5에 저장된 전체 관측과 실제 정책 입력은 구분한다.

## 학습

원본 → annotation → Mimic 성공 시범 → BC-RNN/GMM 순서다. LSTM hidden 400, 2 layers, GMM 5 modes, sequence length 10, batch 100, 학습률 0.001, 목표 epoch 2000을 사용한다.

`train.py`는 `--config`로 JSON을 직접 지정할 수 있다. 지정하지 않으면 task에 등록된 설정을 읽는다. `--algo bc`와 JSON의 `algo_name: bc`를 사용하며, 실제 학습 시드는 `train.seed`에서 읽는다. `--name`은 결과 폴더 이름이다.

시드 101과 100 설정은 [configs/keyboard](../configs/keyboard)에 있다. 동시에 실행할 경우 서로 다른 `--name`을 사용한다. 설정을 준비한 것과 학습·평가 완료는 [학습 상태](training_status.md)에 구분했다.

## 포함한 코드

| 경로 | 역할 |
| --- | --- |
| `isaaclab_project/source/isaaclab_tasks/.../place/` | 과업 등록·관측·종료 조건·BC 설정 |
| `isaaclab_project/source/isaaclab_assets/.../robots/agibot.py` | 로봇 초기 자세·관절 설정 |
| `isaaclab_project/scripts/imitation_learning/robomimic/train.py` | JSON 선택·BC 학습 |
| `isaaclab_project/scripts/imitation_learning/robomimic/play.py` | 정책 평가 |
| `tools/merge_hdf5_datasets.py` | 원본 병합 |

과업 코드의 파일 해시는 [source manifest](../isaaclab_project/source_manifest.json)에 있다. Isaac Sim 엔진과 로봇·물체 USD 자산은 설치된 환경을 사용한다.

[동작 규칙](data_collection.md) · [재현 명령](REPRODUCE.md)
