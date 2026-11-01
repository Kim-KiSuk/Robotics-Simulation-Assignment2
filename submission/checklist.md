# 제출 파일 확인

| 항목 | 위치 |
|---|---|
| 환경·로봇·controller·학습·평가 코드 | `isaaclab_project/` |
| 최종 모델 1개 | `models/final_model.pth` |
| 최종 수집 원본 | Release의 `toy2box_new_rule_100.hdf5` (100개) |
| 모델 해시·학습 입력 정보 | `models/model_manifest.json` |
| 평가 명령어 | `submission/evaluation_command.txt` (`evaluate.txt`에도 같은 내용 보존) |
| 이전 n20 실험 발표 초안 | `submission/toy2box_presentation_draft.pptx` (현재 선택 모델과 구분) |
| 설치·재현 방법 | `docs/REPRODUCE.md` |

## 실행 확인

- 모델 경로와 task 이름을 확인한다.
- 평가 설정은 rollout 100회, horizon 800, 검증 seed 42다.
- 모델 가중치의 SHA256은 manifest와 일치해야 한다.
- Isaac Sim과 로봇·물체 자산은 실행 환경에 설치되어 있어야 한다.

## 결과 정리

선택 모델은 new rule 100개 실험의 run 20261101015656, epoch 2000이다. 모델 로드·config·해시와 기존 rollout 영상 이력을 확인했으며 정식 100회 성공률은 미확정이다. 이전 n20 부분 실행 기록을 현재 모델 결과로 사용하지 않는다. 발표 자료에는 현재 선택 모델, 정식 평가, 실패 단계 분석과 통제 실험 결과를 반영해야 한다.
