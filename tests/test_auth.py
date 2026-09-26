import uuid


def test_me_requires_token(client):
    r = client.get("/me")
    assert r.status_code in (401, 403)


def test_me_rejects_tampered_token(client):
    r = client.get("/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_me_rejects_expired_token(client):
    # craft expired token manually (exp in past)
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings
    exp = datetime.now(timezone.utc) - timedelta(seconds=1)
    tok = pyjwt.encode({"sub": str(uuid.uuid4()), "exp": exp}, settings.secret_key, algorithm="HS256")
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
