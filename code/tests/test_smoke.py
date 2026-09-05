from __future__ import annotations


def test_package_imports() -> None:
    import eqtrace as pkg

    assert pkg.__version__
