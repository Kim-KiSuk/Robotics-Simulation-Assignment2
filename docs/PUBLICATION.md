# 공개 자료와 검증 범위

## 공개한 파일

- 연구 조건 세 개와 스크립트 테스트 조건의 증강 전 수집 원본 HDF5: 20개 조건은 20개, 100개 조건은 100개.
- 각 실험에서 rollout에 사용한 epoch 2000 모델 하나씩.
- 기본 선택 모델 New rule 100의 `models/final_model.pth`와 실제 학습 config.
- 과업 코드 overlay, 데이터 병합·학습·평가·재생 도구, 대표 MP4와 실제 영상 GIF.
- 데이터·모델 해시, 학습 로그 발췌, 원본 재생 판정, 공개 파일 검증 기록.

annotation·Mimic 전체 파일, 중간 epoch 가중치, Isaac Sim 엔진과 외부 USD 자산은 배포에 포함하지 않는다. [Release 검증 기록](../reports/release_publication.json)에서 파일 크기와 GitHub 서버의 SHA256을 확인할 수 있다.

## 결과의 의미

정확한 정책 성공률은 미확정이다. 저장 action 재생 성공, 수집 시도 성공, 영상 조기 종료를 정책 성공률로 바꾸지 않았다. 기본 모델 선택도 고정 epoch와 사용자 지정에 따른 것이며 검증된 최고 성능 순위에 따른 선택이라고 주장하지 않는다.

GIF는 실제 trial 0의 같은 시간 구간이며 영상의 성공 여부로 선별하지 않았다. MP4와 모델의 연결은 실행 이력에 근거하고, 원본 영상 자체에 모델 해시가 있는 것은 아니다.

## 로컬 검사

```bash
python scripts/verify_publication.py
```

Markdown 링크·JSON 파싱, 기본 checkpoint SHA256, 과업 코드 해시, 결과 표와 원본 manifest의 일치, GIF의 원본 MP4·구간·재생 시간을 검사한다. 모델 재평가나 새 성공률 측정은 수행하지 않는다. 결과는 [publication_validation.json](../results/publication_validation.json)에 저장한다.

[상위 manifest](../manifest.json) · [데이터 manifest](../data/experiment_manifest.json) · [모델 manifest](../models/experiment_manifest.json) · [영상 manifest](../artifacts/media/manifest.json)
