from msys2_devtools.utils import vercmp


def test_vercmp():

    def test_ver(a, b, res):
        assert vercmp(a, b) == res
        assert vercmp(b, a) == (res * -1)

    test_ver("1.0.0", "2.0.0", -1)
    test_ver("1.0.0", "1.0.0.r101", -1)
    test_ver("1.0.0", "1.0.0", 0)
    test_ver("2019.10.06", "2020.12.07", -1)
    test_ver("1.3_20200327", "1.3_20210319", -1)
    test_ver("r2991.1771b556", "0.161.r3039.544c61f", -1)
    test_ver("6.8", "6.8.3", -1)
    test_ver("6.8", "6.8.", -1)
    test_ver("2.5.9.27149.9f6840e90c", "3.0.7.33374", -1)
    test_ver(".", "", 1)
    test_ver("0", "", 1)
    test_ver("0", "00", 0)
    test_ver(".", "..0", -1)
    test_ver(".0", "..0", -1)
    test_ver("1r", "1", -1)
    test_ver("r1", "r", 1)
    test_ver("1.1.0", "1.1.0a", 1)
    test_ver("1.1.0.", "1.1.0a", 1)
    test_ver("a", "1", -1)
    test_ver(".", "1", -1)
    test_ver(".", "a", 1)
    test_ver("a1", "1", -1)

    # FIXME:
    # test_ver(".0", "0", 1)
