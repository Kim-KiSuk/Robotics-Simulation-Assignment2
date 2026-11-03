# Agibot Toy2Box 모방학습

**Agibot 오른팔로 트럭을 집어 상자 안에 놓는 정책**을 학습한다. 주된 연구 질문은 **조작자 1명과 다수의 시범으로 학습한 정책의 성능이 다른가**이다. 단일 실험과 혼합 실험을 각각 구성해 사용자 구성에 따른 차이를 비교했다.

원본 시범은 조건마다 **20개**, Mimic 성공 시범은 **500개**로 맞췄다. 학습 seed **101·111** 모델을 각각 평가한 결과, 평균 성공률은 **① 단일 사용자·단일 실험 30.5%, ② 단일 사용자·혼합 실험 43.5%, ③ 다수 사용자·단일 실험 30.0%, ④ 다수 사용자·혼합 실험 38.0%**였다.

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

| 조건 | seed 101 | seed 111 | 평균 ± 표준편차 |
| --- | ---: | ---: | ---: |
| ① 단일 사용자·단일 실험 | 30% (30/100) | 31% (31/100) | **30.5% ± 0.71%p** |
| ② 단일 사용자·혼합 실험 | 43% (43/100) | 44% (44/100) | **43.5% ± 0.71%p** |
| ③ 다수 사용자·단일 실험 | 32% (32/100) | 28% (28/100) | **30.0% ± 2.83%p** |
| ④ 다수 사용자·혼합 실험 | 32% (32/100) | 44% (44/100) | **38.0% ± 8.49%p** |

표준편차는 두 학습 seed를 표본으로 계산한 **표본 표준편차(n−1)**다. 평가 성공률의 신뢰구간이나 rollout 간 표준편차를 뜻하지 않는다. 총 8개 모델을 각각 100회 평가했다.

| 비교 | 평균 성공률 차이 | 관찰 |
| --- | ---: | --- |
| 단일 사용자에서 혼합 비교 · ②−① | **+13.0%p** | 두 seed 모두 혼합 실험이 13%p 높았다. |
| 다수 사용자에서 혼합 비교 · ④−③ | **+8.0%p** | seed 101은 차이가 없었고, seed 111은 혼합 실험이 16%p 높았다. |
| 단일 실험에서 사용자 구성 · ①−③ | **+0.5%p** | 평균은 비슷했고, seed별 우열이 달랐다. |
| 혼합 실험에서 사용자 구성 · ②−④ | **+5.5%p** | seed 101은 단일 사용자가 11%p 높았고, seed 111은 같았다. |

## 3. 가설과 결과 해석

**처음 가설:** 제한된 시범 수에서는 같은 사람이 같은 행동 패턴을 반복한 데이터가 학습에 유리할 것으로 예상했다. 따라서 단일 실험이 혼합 실험보다, 단일 사용자가 다수 사용자보다 높은 성공률을 보일 것으로 가정했다.

**혼합 실험의 결과는 첫 가설과 달랐다.** 단일 사용자에서는 30.5%에서 43.5%로, 다수 사용자에서는 30.0%에서 38.0%로 평균 성공률이 높아졌다. 이번 조건에서는 두 시범 유형을 섞는 것이 평균 성능 저하로 이어지지 않았다. 특히 단일 사용자 혼합 실험은 두 seed에서 모두 같은 폭으로 향상됐다.

**단일 사용자의 뚜렷한 우세는 확인하지 못했다.** 단일 실험에서는 차이가 0.5%p로 작았고, 혼합 실험에서는 단일 사용자가 평균 5.5%p 높았다. 따라서 사용자 구성의 결과까지 전부 예상과 반대였다고 해석하지 않는다. 다수 사용자 혼합 실험은 32%와 44%로 seed에 따른 변동도 컸다.

**가능한 설명:** S1·S2가 서로 다른 접근 자세와 경로의 시범을 제공해 정책이 접하는 상태를 넓혔을 수 있다. 다만 이는 후속 분석이 필요한 가설이다. S2 시범 자체의 난이도, 완료 시간, 파지 위치 등도 결과에 영향을 줄 수 있어, 성능 향상의 원인을 다양성이나 행동 일관성 하나로 확정하지 않는다.

학습 seed가 2개인 결과이므로 통계적 유의성이나 모든 조작자에 대한 일반적 우열을 주장하지 않는다. 이번 실험에서 가장 분명한 관찰은 **단일 사용자 혼합 실험이 두 seed 모두에서 단일 사용자 단일 실험보다 높은 성공률을 보였다는 점**이다.

## 4. 공통 조건과 학습 입력

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

## 5. 프로젝트 실행

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

## 참고

[IsaacLab_RS](https://github.com/cailab-hy/IsaacLab_RS)와 [Isaac Lab](https://github.com/isaac-sim/IsaacLab)을 기반으로 한다. [라이선스](LICENSE)
