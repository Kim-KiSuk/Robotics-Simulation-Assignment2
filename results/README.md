# 실험 요약과 원자료

| 파일 | 내용 |
| --- | --- |
| [experiment_summary.csv](experiment_summary.csv) | 4개 공개 조건의 원본·annotation·학습 수, 시간, idle, 재생 판정 |
| [experiment_summary.json](experiment_summary.json) | 같은 표와 근거 파일 경로 |
| [data_overlap.json](data_overlap.json) | New rule 20과 100의 action·EE 궤적 지문 비교 |
| [publication_validation.json](publication_validation.json) | 링크·모델·과업 코드·실제 영상 GIF의 로컬 검증 |
| [원자료 reports](../reports) | 실행 기록, 모델/데이터 연결, 영상 inventory, Release 검증 |

정책 성공률 열은 확인 전까지 빈 값 또는 `null`이다. 재생 성공 횟수를 정책 성공률로 채우지 않는다. `scripts/build_figures.py`가 공개 manifest에서 요약 표와 그림을 재생성한다.

재평가 시 `--output_root ./results/evaluations`를 지정하면 해당 폴더에 실행별 로그와 trial 판정이 저장된다. [실험 결과](../docs/RESULTS.md) · [평가 명령](../docs/REPRODUCE.md)
