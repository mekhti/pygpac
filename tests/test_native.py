import pygpac


def test_init_and_close():
    pygpac.init()
    try:
        assert pygpac.version()
    finally:
        pygpac.close()


def test_abi_version_is_reported():
    major, minor = pygpac.abi_version()
    assert isinstance(major, int)
    assert isinstance(minor, int)
    assert major > 0


def test_init_is_idempotent():
    pygpac.init()
    pygpac.init()  # should not raise or re-initialize
    pygpac.close()
