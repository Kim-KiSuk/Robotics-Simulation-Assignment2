# 데이터 구성과 학습 입력

## 연구 조건

주 연구 축은 **조작자 1명 vs 다수**다. New rule 100과 Multi operator 100을 주 비교 조건으로 두며, New rule 20은 원본 개수의 보조 조건이고 n100은 스크립트 테스트용이다.

| 조건 | 원본 | Annotation | Mimic 학습 시범 |
| --- | ---: | ---: | ---: |
| New rule 20 | 20 | 19 | 1,000 |
| New rule 100 | 100 | 98 | 1,000 |
| Multi operator | 100 | 93 | 1,000 |
| n100 (스크립트 테스트용) | 100 | 99 | 500 |

다수 조건에 사용한 자료는 new_rule, vertical, 팀원 1, 팀원 2, 조교님 데이터이며 각각 20개씩 총 100개다. 자료 구성은 파일명 대신 위 이름으로 설명한다.

## HDF5와 정책 입력

원본에는 초기 상태·상태 관측·action이 포함된다. action은 상대 이동 3축, 회전 3축과 그리퍼로 구성된 7차원이며 제어 간격은 0.05초다. 원본에 RGB 영상이 없는 경우 저장 action을 Isaac Sim에서 재생해 영상을 생성한다.

정책은 EE 위치·자세, 그리퍼 상태, 트럭 위치·자세, 박스 위치·자세의 23차원 상태를 사용한다. 전체 HDF5 관측 목록과 실제 정책 입력을 구분한다.

## 원본과 학습 데이터

공개 HDF5는 증강 전 원본 20개 또는 100개다. 기본 모델은 원본 100개 → annotation 98개 → Mimic 1,000개로 학습했다. 원본 개수와 학습 시범 개수를 구분한다.

[데이터 manifest](../data/experiment_manifest.json)에는 시범 수·통계·SHA256·다운로드 URL이 있고, [원본/모델 대응](../reports/original_rollout_pairs.json)에는 각 조건의 연결 정보가 있다. 데이터 바이트와 모델 가중치는 그대로 보존한다.

## 관련 자료

- [원본 데이터 다운로드](../artifacts/datasets/README.md)
- [기존 원본 병합](dataset_merge.md)
- [학습·평가 재현](REPRODUCE.md)
- [원본 action 재생 영상](videos.md#실험별-영상)
- [실험 통계](../results/experiment_summary.csv)
