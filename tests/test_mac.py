from mac_change import generate_random_mac


def test_generate_random_mac():
    mac = generate_random_mac()

    parts = mac.split("-")

    assert len(parts) == 6
    assert all(len(part) == 2 for part in parts)
    assert all(c in "0123456789ABCDEF" for part in parts for c in part)

    first_byte = int(parts[0], 16)

    # Unicast
    assert (first_byte & 0x01) == 0

    # Locally administered
    assert (first_byte & 0x02) == 0x02
