import encedo_hem


def test_package_imports() -> None:
    assert isinstance(encedo_hem.__version__, str)
    assert encedo_hem.__version__
