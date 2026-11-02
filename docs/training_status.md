# 학습 확인 범위

## 2026-11-02 확인

| 조건 | 시드 | 확인된 상태 |
| --- | ---: | --- |
| New rule keyboard | 101 | epoch 2000 저장·정상 종료 확인 |
| New rule keyboard · 별도 실행 | 101 | 학습 진행 기록 확인; 위 실행과 같은 시드 |
| New rule keyboard | 100 | 비교 JSON 준비; 실행·완료 기록 미확인 |
| Multi operator keyboard | — | 이번 데이터로 학습한 완료 모델 미확인 |

진행 상태는 아래 근거 파일의 확인 시각 기준이다. 이후 로컬에서 학습이 계속되면 상태가 달라질 수 있다.

[학습 확인 JSON](../reports/keyboard_training_20261102.json) · [학습 로그 발췌](../reports/keyboard_training_20261102.txt)

두 JSON의 알고리즘은 모두 `bc`이고, 실제 시드는 `train.seed`다. 시드 101 설정과 시드 100 설정만으로 두 학습 시드의 결과 평균을 계산하지 않는다. 별도 이름의 동일 시드 학습 역시 독립 시드 실험이 아니다.

## 모델 배포

이번 모델은 rollout 평가 전이므로 최종 배포 가중치를 지정하지 않았다. 현재 저장소에 남아 있는 `models/final_model.pth`와 기존 Release 정보는 [이전 조건](experiments.md)에 해당한다. 이번 keyboard 조건의 모델·영상·성공률로 사용하지 않는다.

[재현 명령](REPRODUCE.md) · [평가 대기](RESULTS.md)
