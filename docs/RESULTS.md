# 데이터 준비 현황과 평가 대기

2026-11-02 확인 기준이다. 아래는 저장 파일과 학습 로그에서 확인한 준비 현황이며 **정책 rollout 결과가 아니다**.

## 데이터와 증강

| 조건 | 원본 | Annotation | Mimic 성공 | Mimic 실패 기록 |
| --- | ---: | ---: | ---: | ---: |
| New rule keyboard | 20 | 17 | 1,000 | 2,616 |
| Multi operator keyboard | 100 | 91 | 1,000 | 2,169 |

두 성공 파일 모두 1,000개의 `success=True` 시범이 저장돼 있다. 실패 파일은 별도이며 학습 성공 시범 수에 포함하지 않았다. Annotation에서 줄어든 원인을 개수만으로 단정하지 않는다.

| 원본 | 총 step | 평균 시간 | 평균 idle |
| --- | ---: | ---: | ---: |
| New rule keyboard | 11,276 | 28.19초 | 30.97% |
| Multi operator keyboard | 60,892 | 30.45초 | 31.44% |

idle은 episode마다 action 앞 6개 성분이 정확히 0인 프레임 비율을 구한 뒤 평균했다. 제어 간격은 0.05초다. [JSON](../results/keyboard_study_20261102.json) · [CSV](../results/keyboard_study_20261102.csv)

## 학습 상태

New rule의 시드 101 모델은 epoch 2000 저장과 학습 정상 종료 기록이 확인됐다. 별도 이름의 동일 시드 실행도 확인됐다. 두 실행을 서로 다른 학습 시드로 세지 않는다. 시드 100은 비교 설정만 준비된 상태이며, 이번 Multi operator 데이터의 학습 완료 모델은 아직 확인되지 않았다.

## 정책 평가

| 조건 | 정책 성공률 | Rollout 영상 | 최종 평가 모델 |
| --- | --- | --- | --- |
| New rule keyboard | 평가 대기 | 없음 | 평가 후 지정 |
| Multi operator keyboard | 평가 대기 | 없음 | 평가 후 지정 |

현재 성능 우열, 개선 폭, 시드 평균은 보고하지 않는다. 기존 조건의 모델·영상·성공률을 이번 keyboard 조건에 연결하지 않는다. [평가 기록 항목](evaluation.md) · [이전 조건 기록](experiments.md)
