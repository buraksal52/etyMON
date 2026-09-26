from app.settings import settings
from app.storage import LocalFilesystemStorageProvider, get_storage_provider


def test_local_storage_provider_persists_private_uploads(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(settings, "storage_public_base_url", "http://localhost:8000")
    monkeypatch.setattr(settings, "storage_provider", "local")
    provider = get_storage_provider()
    assert isinstance(provider, LocalFilesystemStorageProvider)

    key = "events/event/participants/participant/proofs/photo.png"
    provider.put_bytes(key, b"proof", "image/png")

    content, content_type = provider.get_bytes(key)
    assert content == b"proof"
    assert content_type == "image/png"
    assert (
        "/storage/download?key=events%2Fevent%2Fparticipants%2Fparticipant%2Fproofs%2Fphoto.png"
        in provider.get_download_url(key)
    )
