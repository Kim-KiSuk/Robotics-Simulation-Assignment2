# Agibot Toy2Box 모방학습

**Agibot 오른팔로 트럭을 집어 상자 안에 놓는 정책**을 학습한다. 주된 연구 질문은 **조작자 1명과 다수의 시범으로 학습한 정책의 성능이 다른가**이다. 단일 실험과 혼합 실험을 각각 구성해 사용자 구성에 따른 차이를 비교했다.

원본 시범은 조건마다 **20개**, Mimic 성공 시범은 **500개**로 맞췄다. 학습 seed **101·111** 모델을 각각 평가한 결과, 평균 성공률은 **① 단일 사용자·단일 실험 30.5%, ② 단일 사용자·혼합 실험 43.5%, ③ 다수 사용자·단일 실험 30.0%, ④ 다수 사용자·혼합 실험 38.0%**였다.

**핵심 관찰:** 원본 시범 20개 규모에서도 혼합 실험의 평균 성공률이 두 사용자 구성에서 모두 높았다. 이는 이번 조건에서 **단일 행동 패턴의 일관성을 유지하는 것보다 시범 유형의 다양성을 확보하는 것이 더 유리할 수 있다**는 결과 기반 가설을 뒷받침한다.

## 1. 실험 구성

| 조건 | 사용자 구성 | 원본 시범 구성 | 원본 수 | Mimic 성공 시범 |
| --- | --- | --- | ---: | ---: |
| ① 단일 사용자·단일 실험 | 본인 1명 | S1 20개 | 20 | 500 |
| ② 단일 사용자·혼합 실험 | ①과 같은 본인 1명 | S1 10개 + S2 10개 | 20 | 500 |
| ③ 다수 사용자·단일 실험 | 본인 포함 5명, 각 4개 | 전부 S1 | 20 | 500 |
| ④ 다수 사용자·혼합 실험 | ③과 같은 5명, 각 4개 | 각자 S1 2개 + S2 2개 | 20 | 500 |

**단일 실험**은 S1 시범만 사용한 조건이고, **혼합 실험**은 S1·S2 시범을 같은 비율로 합친 조건이다. 혼합 실험도 전체 시범 수는 20개로 유지한다.

| 시범 유형 | 동작 규칙 |
| --- | --- |
| S1 · New rule | **회전 → XY 이동 → 수직 하강 → 그립 → 수직 상승 → 박스 이동 → 릴리즈** |
| S2 · XY 우선 | **XY 이동 → 회전 → 수직 하강 → 그립 → 수직 상승 → 박스 이동 → 릴리즈** |

두 유형 모두 수직 파지를 기준으로 한다. S2에서는 회전 뒤 필요한 경우 XY 위치를 재정렬한다.

사용자 구성은 **①↔③**, **②↔④**로 비교한다. 같은 사용자 구성에서 시범 혼합에 따른 차이는 **①↔②**, **③↔④**로 확인한다.

## 2. 평가 결과

평가 seed는 **42**, 모델마다 **100회 rollout**, 한도는 **800 step**이다. 1 step은 0.05초이므로 최대 40초다. 아래 성공률은 전달받은 평가 종료 집계값이며, 평균과 표준편차는 학습 seed 101·111의 두 성공률에서 계산했다.

| 조건 | 학습 seed 101 성공률 | 학습 seed 111 성공률 | 평균 ± 표준편차 | 평가 seed |
| --- | ---: | ---: | ---: | ---: |
| ① 단일 사용자·단일 실험 | 30% (30/100) | 31% (31/100) | **30.5% ± 0.71%p** | **42** |
| ② 단일 사용자·혼합 실험 | 43% (43/100) | 44% (44/100) | **43.5% ± 0.71%p** | **42** |
| ③ 다수 사용자·단일 실험 | 32% (32/100) | 28% (28/100) | **30.0% ± 2.83%p** | **42** |
| ④ 다수 사용자·혼합 실험 | 32% (32/100) | 44% (44/100) | **38.0% ± 8.49%p** | **42** |

표준편차는 두 학습 seed를 표본으로 계산한 **표본 표준편차(n−1)**다. 평가 성공률의 신뢰구간이나 rollout 간 표준편차를 뜻하지 않는다. 총 8개 모델을 각각 100회 평가했다.

| 비교 | 평균 성공률 차이 | 관찰 |
| --- | ---: | --- |
| 단일 사용자에서 혼합 비교 · ②−① | **+13.0%p** | 두 seed 모두 혼합 실험이 13%p 높았다. |
| 다수 사용자에서 혼합 비교 · ④−③ | **+8.0%p** | seed 101은 차이가 없었고, seed 111은 혼합 실험이 16%p 높았다. |
| 단일 실험에서 사용자 구성 · ①−③ | **+0.5%p** | 평균은 비슷했고, seed별 우열이 달랐다. |
| 혼합 실험에서 사용자 구성 · ②−④ | **+5.5%p** | seed 101은 단일 사용자가 11%p 높았고, seed 111은 같았다. |

## 3. 결과에 따른 가설 수정과 해석

처음에는 제한된 시범 수에서 일관된 행동 패턴을 반복하는 것이 유리할 것으로 예상했다. 그러나 혼합 실험에서 더 높은 평균 성공률이 관찰되어, 결과를 바탕으로 다음 가설을 제시한다.

> **수정 가설:** 원본 시범이 20개인 소규모 조건에서도, 단일 행동 패턴을 반복하는 일관성보다 서로 다른 시범 유형을 균형 있게 포함하는 다양성이 정책 학습에 더 유리할 수 있다.

이는 결과 확인 후 제시한 가설이며, 실험 전에 확정한 예측으로 다루지 않는다. 여기서 다양성은 **S1·S2 시범 유형의 혼합**을 뜻한다. 사용자 수를 늘리는 것과 같은 개념으로 해석하지 않는다.

**가설을 뒷받침하는 관찰:** 단일 사용자에서는 혼합 실험이 30.5%에서 43.5%로 **13%p**, 다수 사용자에서는 30.0%에서 38.0%로 **8%p** 높았다. 전체 시범 수를 늘리지 않고 구성만 나눴는데도, 두 사용자 구성에서 혼합 조건의 평균이 높았다. 특히 단일 사용자는 두 학습 seed 모두 13%p 향상됐다.

**사용자 수와의 관계:** 단일 사용자와 다수 사용자의 차이는 단일 실험에서 0.5%p, 혼합 실험에서 5.5%p였다. 이번 결과는 사용자 수 자체보다 시범 유형을 어떻게 구성했는지에 주목할 근거를 제공하지만, 두 요인의 중요도를 일반적인 순위로 확정한 것은 아니다.

**가능한 설명:** S1·S2가 서로 다른 접근 자세와 경로를 포함해 정책이 접하는 상태를 넓혔을 수 있다. 다만 시범 유형의 혼합과 상태 다양성은 같은 지표가 아니다. S2 시범의 난이도, 완료 시간, 파지 위치도 영향을 줄 수 있어 구체적인 원인은 후속 분석이 필요하다.

**해석 범위:** 학습 seed는 2개이며, 다수 사용자 혼합 실험은 seed별 32%·44%로 변동이 컸다. 따라서 결론은 **이번 20개 원본·Mimic 500개 조건에서 혼합 시범의 평균 성능이 높았으며, 다양성이 일관성보다 유리할 수 있음을 시사한다**로 한정한다.

## 4. 조교님 기준과의 비교

수업에서 제공된 조교님 기준은 **원본 시범 20개 → Mimic 500개 → 정책 평가 100회**, 성공률 **26% (26/100)**다. 평가 seed 42·horizon 800·epoch 2000은 이번 실험과 같다. 다만 공개된 26%는 하나의 평가 집계이며, 학습 seed 101·111의 평균과 표준편차가 제공된 결과는 아니다.

| 비교 대상 | 원본 / Mimic | 성공률 | 평가 seed | 집계 방식 |
| --- | --- | ---: | ---: | --- |
| 조교님 제공 기준 | 20 / 500 | **26% (26/100)** | **42** | 공개된 단일 모델 평가 결과 |
| ① 단일 사용자·단일 실험 | 20 / 500 | **30.5% ± 0.71%p** | **42** | 학습 seed 101·111의 평균 ± 표본 표준편차 |
| ② 단일 사용자·혼합 실험 | 20 / 500 | **43.5% ± 0.71%p** | **42** | 학습 seed 101·111의 평균 ± 표본 표준편차 |
| ③ 다수 사용자·단일 실험 | 20 / 500 | **30.0% ± 2.83%p** | **42** | 학습 seed 101·111의 평균 ± 표본 표준편차 |
| ④ 다수 사용자·혼합 실험 | 20 / 500 | **38.0% ± 8.49%p** | **42** | 학습 seed 101·111의 평균 ± 표본 표준편차 |
| 조교님 데이터 재현 대조군 | 20 / 500 | **학습·평가 대기** | 42 (예정) | 동일 조건으로 두 seed를 학습·평가한 뒤 기입 |

현재 네 조건의 평균은 제공 기준 26%보다 높지만, 단일 공개 결과와 두 seed 평균의 차이만으로 성능 개선을 확정하지 않는다. 사용자 구성과 혼합 여부에 관한 비교는 ①~④끼리 수행하고, 조교님 데이터는 별도의 기준선으로 둔다.

**동일 조건의 재현 비교 절차**

1. 조교님 원본 시범 20개를 annotation하고, 기존 네 조건과 같은 Mimic 생성 설정으로 성공 시범 500개를 준비한다.
2. 이 500개를 공통 입력으로 사용해 학습 seed **101·111을 각각 학습**한다. 모델·epoch·batch 등은 기존 네 조건과 맞춘다.
3. 두 모델을 각각 **평가 seed 42·100회 rollout·horizon 800**으로 평가하고, 평균 ± 표본 표준편차를 위 표에 추가한다.

Mimic 데이터는 한 번 준비해 두 학습에 함께 사용한다. 제공된 26%를 재현 대조군의 실측값으로 대신 쓰지 않는다.

## 5. 공통 조건과 학습 입력

| 항목 | 설정 |
| --- | --- |
| Task | `Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0` |
| 환경·성공 판정·종료 조건 | 조건 간 동일 |
| 원본 / Mimic 성공 시범 | 조건마다 20개 / 500개 |
| 정책 | BC-RNN / GMM |
| LSTM / GMM | hidden 400 · 2 layers / 5 modes |
| 관측 / 행동 | 23차원 / 7차원 |
| Sequence / batch | 10 / 100 |
| 학습률 / epoch | 0.001 / 2000 |
| 학습 seed | 101, 111 |
| 평가 seed / rollout / horizon | 42 / 모델마다 100회 / 800 step |

8개 모델의 저장된 학습 설정에서 알고리즘·관측 설정과 epoch·batch·sequence가 같은 것을 확인했다. 학습 로그에서 각 조건의 입력 시범 수를, 실행 기록에서 평가 seed·rollout·horizon을 확인했다.

| 조건 | 학습에 사용한 Mimic 파일 |
| --- | --- |
| ① | `toy2box_agibot_mimic_new_rule_500.hdf5` |
| ② | `toy2box_agibot_mimic_single_mixed_500.hdf5` |
| ③ | `toy2box_agibot_mimic_multi_operator_c3_20_500.hdf5` |
| ④ | `toy2box_agibot_mimic_multi_operator_c4_20_500.hdf5` |

각 파일이 로컬에 준비된 상태에서 아래 명령의 `--dataset`만 해당 조건으로 바꾼다. 학습 seed는 과업 설정 JSON의 `train.seed`에서 지정한다.

```bash
./isaaclab.sh -p scripts/imitation_learning/robomimic/train.py \
    --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 \
    --algo bc \
    --dataset ./datasets/toy2box_agibot_mimic_new_rule_500.hdf5
```

seed별 결과와 계산값은 `results/experiment_results.json`에 저장했다.

## 6. 최종 데이터셋과 모델

조건별 원본 시범 20개와, 위 성공률을 평가한 **epoch 2000 모델 8개**를 저장소에 직접 포함했다. 모델 파일명에는 조건 번호와 학습 seed를 표시했다.

| 조건 | 원본 데이터셋 · 각 20개 | 학습 seed 101 모델 | 학습 seed 111 모델 |
| --- | --- | --- | --- |
| ① 단일 사용자·단일 실험 | [toy2box_agibot_c1.hdf5](datasets/toy2box_agibot_c1.hdf5) | [c1 · seed 101](models/toy2box_agibot_c1_seed101.pth) | [c1 · seed 111](models/toy2box_agibot_c1_seed111.pth) |
| ② 단일 사용자·혼합 실험 | [toy2box_agibot_c2.hdf5](datasets/toy2box_agibot_c2.hdf5) | [c2 · seed 101](models/toy2box_agibot_c2_seed101.pth) | [c2 · seed 111](models/toy2box_agibot_c2_seed111.pth) |
| ③ 다수 사용자·단일 실험 | [toy2box_agibot_c3.hdf5](datasets/toy2box_agibot_c3.hdf5) | [c3 · seed 101](models/toy2box_agibot_c3_seed101.pth) | [c3 · seed 111](models/toy2box_agibot_c3_seed111.pth) |
| ④ 다수 사용자·혼합 실험 | [toy2box_agibot_c4.hdf5](datasets/toy2box_agibot_c4.hdf5) | [c4 · seed 101](models/toy2box_agibot_c4_seed101.pth) | [c4 · seed 111](models/toy2box_agibot_c4_seed111.pth) |

HDF5는 수집 원본이며, 학습에는 원본을 annotation한 뒤 생성한 Mimic 500개를 사용했다. 공개 원본은 로컬 출처 경로만 익명 식별자로 바꾸고 관측·행동·초기 상태 배열은 유지했다. 모델 파일은 평가한 checkpoint 그대로다. 파일 크기와 SHA-256은 `results/experiment_results.json`에 기록했다.

## 7. 정책 성공 예시

상자 투입과 그리퍼 릴리즈가 영상에서 확인되는 예시를 **조건별 한 개씩** 골랐다. 모두 **학습 seed 101·평가 seed 42** 모델의 영상이다. GIF는 마지막 6초를 원래 속도로 보여주며, 클릭하면 전체 MP4로 이동한다. 성공률은 선별 영상이 아닌 전체 100회 평가 집계값을 사용한다.

| ① 단일 사용자·단일 실험 | ② 단일 사용자·혼합 실험 |
| --- | --- |
| [![조건 1 성공 예시](artifacts/media/toy2box_agibot_c1_success.gif)](videos/toy2box_agibot_c1_success.mp4) | [![조건 2 성공 예시](artifacts/media/toy2box_agibot_c2_success.gif)](videos/toy2box_agibot_c2_success.mp4) |
| **Trial 17 · 전체 19.90초 · 평가 seed 42** | **Trial 35 · 전체 15.00초 · 평가 seed 42** |

| ③ 다수 사용자·단일 실험 | ④ 다수 사용자·혼합 실험 |
| --- | --- |
| [![조건 3 성공 예시](artifacts/media/toy2box_agibot_c3_success.gif)](videos/toy2box_agibot_c3_success.mp4) | [![조건 4 성공 예시](artifacts/media/toy2box_agibot_c4_success.gif)](videos/toy2box_agibot_c4_success.mp4) |
| **Trial 99 · 전체 23.45초 · 평가 seed 42** | **Trial 29 · 전체 14.85초 · 평가 seed 42** |

## 8. 프로젝트 실행

Isaac Sim과 Toy2Box 자산이 설치된 수업용 `lerobot-arena` 환경을 사용한다. 이 저장소 자체가 IsaacLab_RS 프로젝트이며 `source/`, `scripts/`, `isaaclab.sh`, `datasets/`, `models/`, `videos/`를 포함한다. Isaac Sim 엔진과 외부 자산은 별도 설치한다.

```bash
conda activate lerobot-arena
cd ~
git clone https://github.com/Kim-KiSuk/Robotics-Simulation-Assignmnet2.git IsaacLab_RS_Toy2Box
cd ~/IsaacLab_RS_Toy2Box
```

수업 환경에 설치된 의존성을 유지하면서 현재 프로젝트의 Python 패키지 경로를 등록한다.

```bash
./isaaclab.sh -p -m pip install --no-deps \
    -e source/isaaclab \
    -e source/isaaclab_assets \
    -e source/isaaclab_tasks \
    -e source/isaaclab_mimic
```

학습 명령은 과업에 등록된 설정을 읽는다. 학습 seed는 아래 JSON의 `train.seed`에서 지정한다.

```text
source/isaaclab_tasks/isaaclab_tasks/manager_based/manipulation/place/config/agibot/agents/robomimic/bc_rnn_low_dim.json
```

**정책 평가 예시:** 조건 ①의 학습 seed 101 모델을 평가 seed 42로 실행한다. 다른 조건은 `--checkpoint`의 파일명과 영상 저장 폴더를 바꾼다.

```bash
./isaaclab.sh -p scripts/imitation_learning/robomimic/play.py \
    --task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0 \
    --checkpoint ./models/toy2box_agibot_c1_seed101.pth \
    --num_rollouts 100 \
    --horizon 800 \
    --seed 42 \
    --video \
    --video_length 1000 \
    --video_folder ./videos/toy2box_agibot_c1_seed101 \
    --headless
```

## 참고

[IsaacLab_RS](https://github.com/cailab-hy/IsaacLab_RS)와 [Isaac Lab](https://github.com/isaac-sim/IsaacLab)을 기반으로 한다. [라이선스](LICENSE)
