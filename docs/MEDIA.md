# 실제 정책 영상과 시범 재생

## README의 정책 GIF

각 실험의 trial 0에서 같은 **8~14초 구간**을 추출했다. 원본은 20 fps이며 GIF는 10 fps로 표본화해 원래 속도 6초를 유지한다. 성공 여부로 구간이나 trial을 고르지 않았으며, 모든 영상이 성공 사례라는 의미는 아니다.

| 실험 | GIF | 전체 정책 MP4 |
| --- | --- | --- |
| New rule 20 | [미리보기](../artifacts/media/new_rule_20_preview.gif) | [trial 0](../videos/experiments/new_rule_20/rollout-episode-0.mp4) · [trial 1](../videos/experiments/new_rule_20/rollout-episode-1.mp4) |
| New rule 100 | [미리보기](../artifacts/media/new_rule_100_preview.gif) | [trial 0](../videos/experiments/new_rule_100/rollout-episode-0.mp4) · [trial 1](../videos/experiments/new_rule_100/rollout-episode-1.mp4) |
| Multi operator | [미리보기](../artifacts/media/multi_operator_100_preview.gif) | [trial 0](../videos/experiments/multi_operator_100/rollout-episode-0.mp4) · [trial 1](../videos/experiments/multi_operator_100/rollout-episode-1.mp4) |

MP4에 checkpoint 해시가 내장돼 있지 않아 모델 연결은 보존된 실행 명령 이력을 근거로 한다. n100 (스크립트 테스트용) 공용 영상 폴더는 다른 모델 평가에도 쓰여 특정 모델의 미리보기로 게시하지 않는다. 원본·모델은 해당 조건의 Release에서 제공한다.

전체 MP4에는 검은 시작 프레임이 포함된 파일이 있다. GIF는 고정된 8초 지점에서 시작한다. 이미지 내용이나 물체 위치를 생성·합성한 영상이 아니다. [미리보기 manifest](../artifacts/media/manifest.json)에는 원본 MP4·GIF 해시, 구간, 속도와 모델 연결 근거가 있다.

## 원본 action 재생 영상

수집 HDF5의 초기 상태를 복원하고 저장 action을 실행한 영상은 [기존 영상 안내](videos.md#실험별-영상)에 있다. New rule 20·100, Multi operator의 첫 번째·마지막 episode를 제공한다.

이 재생 검증과 정책이 관측에 따라 행동을 결정한 독립 평가를 구분한다. 전체 재생 판정은 [replay inventory](../reports/replay_inventory.json), 정책 영상의 프레임 수는 [policy inventory](../reports/policy_video_inventory.json)에 있다.

## 재생성

```bash
python scripts/build_previews.py
```

저장소에 포함된 MP4에서만 GIF를 다시 만든다. 시뮬레이터나 GPU는 필요하지 않으며 OpenCV와 Pillow를 사용한다. HDF5에서 실제 action 재생 MP4를 만들 때는 Isaac Sim이 필요하다. [HDF5 재생 명령](reproduction.md#실제-시범-mp4-재생성)
