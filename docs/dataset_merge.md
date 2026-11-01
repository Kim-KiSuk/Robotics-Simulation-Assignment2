# 기존 원본 데이터 병합

다수 조건은 new_rule, vertical, 팀원 1, 팀원 2, 조교님 데이터를 각각 20개씩 합친 총 100개다.

병합 도구는 기존 HDF5의 episode를 복사한다. 새 로봇 동작이나 시범을 생성하는 도구가 아니며, Python과 h5py만으로 실행한다.

```bash
python tools/merge_hdf5_datasets.py \
  --input_files source_01.hdf5 source_02.hdf5 source_03.hdf5 \
                source_04.hdf5 source_05.hdf5 \
  --output_file ./data/multi_operator_100_repeat.hdf5
```

입력 데이터의 task, 관측/action 구성과 제어 간격을 맞춰야 한다. 도구는 task 이름과 action shape를 검사하고, episode를 연속 번호로 다시 매기며 원본 파일·episode 속성을 남긴다. 출력 파일이 이미 있으면 중단한다.

task 메타데이터가 빠졌다면 원본이 같은 task인지 확인한 뒤 `--task Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0`를 지정한다. 서로 다른 task가 기록된 입력은 이 옵션으로도 통과하지 않는다.

[데이터 구성](data_collection.md) · [학습과 평가](REPRODUCE.md)
