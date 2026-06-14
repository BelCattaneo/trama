import hashlib

import pytest

from trama.storage import LocalStorage


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_save_returns_prefixed_ref(tmp_path):
    storage = LocalStorage(tmp_path)
    content = b"hello"
    h = sha256(content)
    ref = storage.save(content, h)
    assert ref == f"{h[:2]}/{h}"
    assert (tmp_path / h[:2] / h).read_bytes() == content


def test_get_returns_saved_bytes(tmp_path):
    storage = LocalStorage(tmp_path)
    content = b"some bytes here"
    h = sha256(content)
    ref = storage.save(content, h)
    assert storage.get(ref) == content


def test_exists_before_and_after_save(tmp_path):
    storage = LocalStorage(tmp_path)
    content = b"hola"
    h = sha256(content)
    ref = f"{h[:2]}/{h}"
    assert storage.exists(ref) is False
    storage.save(content, h)
    assert storage.exists(ref) is True


def test_exists_false_for_unknown_ref(tmp_path):
    storage = LocalStorage(tmp_path)
    assert storage.exists("00/never-existed") is False


def test_second_save_is_no_op(tmp_path):
    storage = LocalStorage(tmp_path)
    content = b"dedup me"
    h = sha256(content)
    ref1 = storage.save(content, h)
    final = tmp_path / h[:2] / h
    mtime_before = final.stat().st_mtime_ns
    ref2 = storage.save(content, h)
    assert ref1 == ref2
    assert final.stat().st_mtime_ns == mtime_before


def test_prefix_dir_created_if_absent(tmp_path):
    storage = LocalStorage(tmp_path / "nested" / "storage")
    content = b"creates dirs"
    h = sha256(content)
    storage.save(content, h)
    assert (tmp_path / "nested" / "storage" / h[:2] / h).is_file()


def test_save_rejects_non_hex_hash(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.save(b"x", "not-a-hash")


def test_save_rejects_wrong_length_hash(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.save(b"x", "ab" * 31)  # 62 chars


def test_save_rejects_uppercase_hash(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.save(b"x", "A" * 64)


def test_get_rejects_traversal_ref(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.get("../etc/passwd")


def test_get_rejects_absolute_ref(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.get("/etc/passwd")


def test_exists_rejects_traversal_ref(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.exists("../escape")


def test_no_tmp_visible_after_failed_write(tmp_path, monkeypatch):
    import os

    storage = LocalStorage(tmp_path)
    content = b"will fail mid-write"
    h = sha256(content)

    real_rename = os.rename

    def boom(*args, **kwargs):
        raise RuntimeError("simulated crash before rename")

    monkeypatch.setattr(os, "rename", boom)
    with pytest.raises(RuntimeError):
        storage.save(content, h)
    monkeypatch.setattr(os, "rename", real_rename)

    ref = f"{h[:2]}/{h}"
    assert storage.exists(ref) is False
    assert list(tmp_path.rglob("*.tmp")) == []
