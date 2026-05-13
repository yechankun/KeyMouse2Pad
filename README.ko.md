# KeyMouse2Pad

[English](README.md) | 한국어

KeyMouse2Pad는 Windows에서 키보드와 마우스 입력을 게임패드 조작으로
변환하는 오픈소스 컨버터입니다. 간단한 GUI, 자유로운 매핑 설정, Windows 전체
입력 캡처를 목표로 합니다.

## 현재 상태

- Windows 중심 GUI 애플리케이션입니다.
- Windows 전역 키보드/마우스 캡처를 지원합니다.
- `vgamepad` / ViGEm 환경이 있으면 Xbox 360 컨트롤러 출력으로 동작합니다.
- 키보드와 마우스 버튼별 매핑을 GUI에서 수정하고 저장할 수 있습니다.
- 핵심 매핑 엔진은 C++ 테스트로 검증합니다.
- 향후 커널 드라이버 개발을 위한 Windows HID 드라이버 경계 코드가 포함되어 있습니다.

이 프로젝트는 아직 서명된 프로덕션 커널 드라이버가 아닙니다. 대상 게임이나
앱에 따라 관리자 권한이 필요할 수 있습니다.

## 실행

Windows:

```bat
run_gui.bat
```

Linux/WSL에서는 매핑 엔진 테스트는 가능하지만, 실제 전역 입력 캡처와 컨트롤러
출력 기능은 Windows 전용입니다.

## 빌드

Windows 실행 파일 빌드:

```bat
build_exe.bat
```

결과물:

```text
dist\KeyMouse2Pad.exe
```

간단한 GUI self-test:

```powershell
py -3 gui\converter_gui.py --self-test
```

## 문서

- [Windows 설치 안내](docs/setup-windows.ko.md)
- [Architecture](docs/architecture.md)
- [Branching](docs/branching.md)
- [English Windows setup](docs/setup-windows.md)

## 기여

무거운 절차보다 작은 PR과 자동화된 검증을 우선합니다. 버그는 재현 방법을 중심으로
이슈를 열고, PR은 한 가지 변경에 집중해 주세요.

자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 라이선스

KeyMouse2Pad는 GNU General Public License v3.0 or later로 배포됩니다.
자세한 내용은 [LICENSE](LICENSE)를 확인하세요.

서드파티 런타임 고지는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)를
확인하세요.
