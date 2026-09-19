# iptime-wan-mac-remote-changer

# ipTIME WAN MAC Remote Changer

**Python + Termux + WireGuard + DDNS를 이용한 ipTIME WAN MAC 원격 변경 자동화**

ipTIME 공유기의 관리자 페이지에서 수행하던 WAN MAC 주소 변경 작업을 Python으로 자동화하고, WireGuard VPN을 이용해 외부 네트워크에서도 공유기에 접속하여 MAC 주소를 변경할 수 있도록 만든 개인 프로젝트입니다.

> **Tested on:** ipTIME A8004T-XR
> **Firmware:** 14.27.6
> **Client:** Android / Termux
> **Language:** Python 3.13

---

## 프로젝트를 만든 이유

ipTIME 관리자 페이지에서 WAN MAC 주소를 변경하면 ISP에서 새로운 공인 IP 주소를 할당받는 경우가 있습니다.

처음에는 단순히 다음 작업을 자동화하는 것이 목적이었습니다.

```text
로그인
  ↓
현재 WAN MAC 확인
  ↓
새 MAC 생성
  ↓
WAN MAC 변경
```

하지만 실제로 원격에서 사용하려고 하니 추가적인 문제가 발생했습니다.

```text
WAN MAC 변경
    ↓
공인 IP 변경
    ↓
기존 WireGuard Endpoint 무효화
    ↓
원격 접속 끊김
```

이 문제를 해결하기 위해 WireGuard와 DDNS를 함께 구성했습니다.

---

## 최종 구조

```text
                    ┌──────────────────────┐
                    │   Android / Termux   │
                    │                      │
                    │    mac_change.py     │
                    └──────────┬───────────┘
                               │
                    WireGuard VPN
                               │
                               ▼
                    ┌──────────────────────┐
                    │      ipTIME Router   │
                    │                      │
                    │    A8004T-XR         │
                    │                      │
                    │    service.cgi      │
                    └──────────┬───────────┘
                               │
                         WAN MAC 변경
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Public IP 변경     │
                    └──────────┬───────────┘
                               │
                              DDNS
                               │
                               ▼
                    WireGuard 재접속
```

---

## 동작 방식

Python `requests`를 사용하여 ipTIME의 관리자 페이지에서 사용하는 CGI API에 HTTP POST 요청을 보냅니다.

주요 API 흐름은 다음과 같습니다.

### 1. 로그인

```text
session/login
```

사용자가 입력한 관리자 ID와 비밀번호를 이용하여 인증합니다.

비밀번호는 코드에 저장하지 않고 실행 시 `getpass`를 통해 입력받습니다.

---

### 2. 인증 상태 확인

```text
session/login
session/info
```

ipTIME의 로그인 과정에서 필요한 인증 절차를 수행하고 현재 세션의 인증 상태를 확인합니다.

---

### 3. 현재 WAN 설정 확인

```text
network/interface/wan1/info
```

현재 WAN 설정을 조회하고 기존 MAC 주소를 확인합니다.

---

### 4. 새로운 MAC 주소 생성

Python의 `secrets` 모듈을 이용하여 랜덤 MAC 주소를 생성합니다.

첫 번째 바이트에는 다음 조건을 적용합니다.

```python
mac[0] = (mac[0] & 0xFC) | 0x02
```

이를 통해 생성된 주소가 **Locally Administered + Unicast** MAC이 되도록 합니다.

---

### 5. WAN MAC 변경

```text
network/interface/wan1/config
```

현재 WAN 설정을 그대로 복사한 뒤 MAC 주소만 새로운 값으로 변경하여 전송합니다.

이렇게 하면 기존 DHCP, MTU 등의 WAN 설정을 최대한 유지하면서 MAC만 변경할 수 있습니다.

---

## 중요한 문제: MAC 변경 후 연결이 끊기는 이유

WAN MAC을 변경하면 공유기의 WAN 인터페이스가 재연결되면서 인터넷 연결이 잠시 끊길 수 있습니다.

또한 ISP에서 새로운 공인 IP를 할당하면 기존 WireGuard Endpoint가 더 이상 현재 공유기를 가리키지 않게 됩니다.

예:

```text
기존

WireGuard
    ↓
112.xxx.xxx.xxx:46733


MAC 변경


새로운 WAN IP

119.xxx.xxx.xxx:46733
```

고정 IP를 Endpoint에 입력해 놓으면 이 시점에서 원격 접속이 끊깁니다.

---

## DDNS를 이용한 해결

WireGuard Endpoint를 공인 IP 주소가 아닌 DDNS hostname으로 지정합니다.

```text
<YOUR_IPTIME_DDNS_HOSTNAME>:46733
```

그러면 WAN IP가 변경되어도 DDNS가 현재 공인 IP를 가리키도록 할 수 있습니다.

따라서 다음과 같은 구조가 됩니다.

```text
WireGuard
    ↓
DDNS hostname
    ↓
현재 WAN IP
    ↓
ipTIME
```

공인 IP가 변경되어도 WireGuard 설정 자체를 매번 수정할 필요가 없습니다.

---

## WireGuard 동작

외부에서 사용할 때:

```text
Galaxy S25 Ultra
      │
     5G
      │
      ▼
WireGuard
      │
      ▼
ipTIME LAN
      │
      ▼
192.168.0.1
```

WireGuard의 Allowed IP는 필요한 내부 네트워크만 VPN을 통해 전달하도록 구성할 수 있습니다.

예:

```text
10.234.177.0/24
192.168.0.0/24
```

따라서 일반적인 5G 인터넷 트래픽은 VPN을 통하지 않고, 공유기 관리 및 내부 네트워크 접근에 필요한 트래픽만 WireGuard를 사용할 수 있습니다.

---

## 외부에서 사용하는 방법

### 1. 5G 사용

휴대폰 Wi-Fi를 끄고 모바일 네트워크를 사용합니다.

### 2. WireGuard 활성화

WireGuard VPN을 ON 합니다.

### 3. Python 실행

```bash
python ~/mac_change.py
```

### 4. 관리자 인증

프로그램이 요청하는 공유기 ID와 비밀번호를 입력합니다.

### 5. MAC 변경

프로그램이 자동으로 새로운 WAN MAC을 생성하고 적용합니다.

WAN 재연결 과정에서 WireGuard 연결이 끊길 수 있습니다.

### 6. WireGuard 재접속

WireGuard를

```text
OFF → ON
```

하여 다시 연결합니다.

DDNS를 사용하기 때문에 변경된 공인 IP를 직접 확인해서 Endpoint를 수정할 필요가 없습니다.

---

## 집에서 사용하는 방법

휴대폰을 공유기 Wi-Fi에 연결한 상태에서도 실행할 수 있습니다.

```bash
python ~/mac_change.py
```

이 경우 휴대폰이 공유기의 LAN에 직접 연결되어 있으므로 WireGuard가 필요하지 않습니다.

---

## Termux 설치

Termux에서 Python과 requests를 설치합니다.

```bash
pkg update
pkg install python
pip install requests
```

스크립트를 Termux 홈 디렉터리에 넣습니다.

```bash
cp ~/storage/downloads/mac_change.py ~/
```

실행:

```bash
python ~/mac_change.py
```

---

## 보안 주의사항

이 프로젝트를 실제 환경에서 사용할 경우 다음 정보는 절대로 GitHub에 업로드하지 않는 것을 권장합니다.

* 공유기 관리자 비밀번호
* WireGuard Private Key
* WireGuard 설정 파일
* 세션 쿠키
* 실제 공인 IP
* 개인 DDNS hostname
* 개인 네트워크 구성 정보

이 저장소의 예제에서는 개인 인증정보를 코드에 저장하지 않습니다.

---

## API 분석 과정

이 프로젝트의 API는 공개 API 문서를 보고 구현한 것이 아니라, 실제 ipTIME 관리자 페이지에서 MAC 주소를 변경하는 과정에서 브라우저의 개발자 도구를 이용하여 네트워크 요청을 확인하는 방식으로 분석했습니다.

브라우저의:

```text
Developer Tools
    ↓
Network
    ↓
MAC 변경 적용
    ↓
HTTP Request 확인
```

과정을 통해 관리자 페이지가 실제로 어떤 요청을 보내는지 확인했습니다.

그 결과 WAN 설정 변경에 사용되는 CGI 요청과 JSON 구조를 확인할 수 있었습니다.

---

## 프로젝트에서 해결한 문제

### 문제 1. 관리자 페이지 작업 자동화

수동으로 관리자 페이지에 들어가 MAC 주소를 변경해야 했습니다.

→ Python `requests`로 CGI API 호출을 자동화했습니다.

### 문제 2. 로그인 세션

단순히 MAC 변경 API만 호출해서는 정상적으로 작업할 수 없었습니다.

→ 로그인 및 인증 상태 확인 과정을 구현했습니다.

### 문제 3. WAN MAC 변경 후 연결 끊김

MAC 변경과 동시에 WAN 연결이 재시작되었습니다.

→ HTTP timeout이 발생할 수 있는 상황을 정상적인 WAN 재연결 과정으로 처리했습니다.

### 문제 4. 공인 IP 변경

MAC 변경 후 ISP에서 새로운 공인 IP를 할당했습니다.

→ WireGuard Endpoint에 DDNS hostname을 사용했습니다.

### 문제 5. WireGuard 연결 끊김

WAN IP 변경으로 기존 VPN 터널이 끊겼습니다.

→ WireGuard를 OFF → ON 하여 새로운 DDNS 주소로 재접속하도록 구성했습니다.

---

## 제한사항

이 프로젝트는 특정 ipTIME 모델 및 펌웨어에서 확인한 동작을 기반으로 합니다.

현재 테스트 환경:

```text
Router: ipTIME A8004T-XR
Firmware: 14.27.6
```

다른 모델이나 펌웨어에서는 API 구조나 인증 방식이 다를 수 있습니다.

또한 WAN MAC 변경 후 새로운 공인 IP가 반드시 할당된다고 보장할 수는 없습니다. ISP의 DHCP 정책 및 네트워크 환경에 따라 결과가 달라질 수 있습니다.

---

## Disclaimer

이 프로젝트는 개인 네트워크 환경에서의 자동화 및 학습 목적으로 작성되었습니다.

공유기의 관리자 API는 펌웨어에 따라 변경될 수 있으며, 이 프로젝트가 모든 ipTIME 모델에서 동작한다고 보장하지 않습니다.
