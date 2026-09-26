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


def test_signup_login_me_student(client):
    r = client.post("/auth/signup", json={"name": "Arjun", "email": "arjun@x.com", "password": "password123", "role": "student"})
    assert r.status_code == 201, r.text
    me = r.json()
    assert me["email"] == "arjun@x.com"
    assert "hashed_password" not in r.text

    r = client.post("/auth/login", json={"email": "arjun@x.com", "password": "password123"})
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"

    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["role"] == "student"


def test_signup_duplicate_case_insensitive(client):
    client.post("/auth/signup", json={"name": "A", "email": "dup@x.com", "password": "password123"})
    r = client.post("/auth/signup", json={"name": "B", "email": "DUP@x.com", "password": "password123"})
    assert r.status_code == 400


def test_login_wrong_password_generic_401(client):
    client.post("/auth/signup", json={"name": "A", "email": "w@x.com", "password": "password123"})
    r = client.post("/auth/login", json={"email": "w@x.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_inactive_user_blocked(client, db_session):
    from app.core.security import hash_password
    from app.models.user import User
    u = User(name="Z", email="z@x.com", hashed_password=hash_password("password123"), role="student", is_active=False)
    db_session.add(u)
    db_session.commit()
    r = client.post("/auth/login", json={"email": "z@x.com", "password": "password123"})
    assert r.status_code == 401


def test_admin_ping_student_forbidden(client):
    client.post("/auth/signup", json={"name": "S", "email": "s@x.com", "password": "password123", "role": "student"})
    tok = client.post("/auth/login", json={"email": "s@x.com", "password": "password123"}).json()["access_token"]
    r = client.get("/admin/ping", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


def test_admin_ping_admin_ok(client):
    client.post("/auth/signup", json={"name": "Root", "email": "root@x.com", "password": "password123", "role": "admin"})
    tok = client.post("/auth/login", json={"email": "root@x.com", "password": "password123"}).json()["access_token"]
    r = client.get("/admin/ping", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
