# 공개 자료와 확인 범위

## 이번 공개 자료

- New rule keyboard 원본 20개와 Multi operator keyboard 원본 100개, SHA256SUMS.
- 자료 구성·동작 규칙·annotation 및 Mimic 개수·원본 통계.
- 시드 101·100 학습 JSON, JSON 선택을 지원하는 학습 코드.
- 학습 완료·진행·준비를 구분한 기록과 재현 명령.

원본 HDF5는 파일 내용 그대로 복사했다. 이번 정책 rollout은 아직 없어 새 모델 가중치·영상·성공률은 추가하지 않았다. 평가 후 checkpoint와 결과를 연결한다.

[현재 파일 기록](../results/keyboard_study_20261102.json) · [학습 확인](../reports/keyboard_training_20261102.json) · [원본 다운로드](../data/README.md)

## 이전 자료와의 구분

기존 모델·영상·실험 manifest는 별도 조건의 이력이다. 이번 keyboard 조건의 정책 결과로 사용하지 않는다. [이전 조건 기록](experiments.md)

## 검사

Markdown 상대 링크·JSON 파싱·원본 SHA256·포함 코드 SHA256과 데이터 개수를 확인한다. 저장된 성공 시범 수는 정책 성공률이 아니다. 기존 배포 자료의 링크·모델·코드 검사는 `python scripts/verify_publication.py`로 수행한다.
