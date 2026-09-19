import copy
import getpass
import secrets
import sys

import requests


ROUTER = "http://192.168.0.1"
URL = f"{ROUTER}/cgi/service.cgi"

HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Origin": ROUTER,
    "Referer": f"{ROUTER}/ui/wan",
}


def generate_random_mac():
    mac = [secrets.randbits(8) for _ in range(6)]

    # Locally Administered + Unicast
    mac[0] = (mac[0] & 0xFC) | 0x02

    return "-".join(f"{x:02X}" for x in mac)


def request(session, method, params=None, timeout=10):
    payload = {"method": method}

    if params is not None:
        payload["params"] = params

    response = session.post(
        URL,
        headers=HEADERS,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()
    return response.json()


def login(session):
    print("라우터 로그인 중...")

    router_id = input("라우터 ID: ")
    router_pw = getpass.getpass("라우터 비밀번호: ")

    result = request(
        session,
        "session/login",
        {
            "id": router_id,
            "pw": router_pw,
        },
    )

    if result.get("result") != "done":
        print("1차 로그인 실패:")
        print(result)
        return False

    print("1차 로그인 성공")

    result = request(
        session,
        "session/login",
    )

    if result.get("result") != "done":
        print("2차 로그인 실패:")
        print(result)
        return False

    print("2차 로그인 성공")

    info = request(
        session,
        "session/info",
    )

    session_info = info.get("result")

    if not session_info or session_info.get("level") != "auth":
        print("인증 상태 확인 실패:")
        print(info)
        return False

    print("인증 상태 확인 완료")

    return True


def get_wan_config(session):
    result = request(
        session,
        "network/interface/wan1/info",
    )

    if result.get("result") is not None:
        return result["result"]

    print("WAN 설정 조회 실패:")
    print(result)

    return None


def main():
    print("=" * 50)
    print("ipTIME WAN MAC 자동 변경")
    print("Termux / WireGuard 원격 사용")
    print("=" * 50)
    print()

    session = requests.Session()

    try:
        if not login(session):
            sys.exit(1)

    except requests.RequestException as e:
        print("로그인 네트워크 오류:")
        print(e)
        sys.exit(1)

    print()

    print("현재 WAN 설정을 확인하는 중...")

    try:
        current = get_wan_config(session)

    except requests.RequestException as e:
        print("WAN 설정 조회 실패:")
        print(e)
        sys.exit(1)

    if current is None:
        sys.exit(1)

    old_mac = current.get("mac")

    print("현재 MAC:", old_mac)
    print("현재 WAN 상태:", current.get("link"))

    new_mac = generate_random_mac()

    print()
    print("새 MAC:", new_mac)

    wan_config = copy.deepcopy(current)
    wan_config["mac"] = new_mac

    print()
    print("WAN MAC 변경 요청...")

    try:
        result = request(
            session,
            "network/interface/wan1/config",
            wan_config,
            timeout=10,
        )

        if result.get("error"):
            print("WAN MAC 변경 API 오류:")
            print(result)
            sys.exit(1)

        print("WAN MAC 변경 요청 완료!")

    except requests.exceptions.ReadTimeout:
        print("MAC 변경과 동시에 연결이 끊겼습니다.")
        print("WAN 재연결 과정으로 보입니다.")

    except requests.RequestException as e:
        print("MAC 변경 중 연결 오류:")
        print(e)
        print()
        print("WAN 재연결 과정에서 발생했을 가능성이 있습니다.")

    print()
    print("=" * 50)
    print("MAC 변경 작업 완료")
    print("=" * 50)
    print("이전 MAC :", old_mac)
    print("새 MAC   :", new_mac)
    print()
    print("WAN 재연결로 WireGuard가 끊길 수 있습니다.")
    print("원격 사용 시 WireGuard를 OFF → ON 하여 재접속하세요.")
    print("=" * 50)


if __name__ == "__main__":
    main()
