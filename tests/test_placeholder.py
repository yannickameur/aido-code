import aido_code


def test_package_is_importable_and_versioned():
    assert isinstance(aido_code.__version__, str)
    assert aido_code.__version__
