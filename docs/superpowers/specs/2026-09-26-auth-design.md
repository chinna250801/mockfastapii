# Step 1 Auth Design — Mock Test Platform V1

Date: 2026-09-26
Status: Approved (Approach A — JWT Bearer reuse)
PRD refs: §5, §6.1

## 1. Understanding (agreed)
- Outcome: student/admin can signup/login, receive JWT, call role-guarded routes.
- What user said: go step-by-step, Step 1 = Auth, Approach A.
- Assumptions: reuse `app/core/security.py` (bcrypt + HS256 JWT, 60min expiry) and `users` table as-is. No DB change.
- Success: full cycle signup → login → GET /me works; duplicate/wrong-password/inactive/expired handled; student blocked from admin routes.

## 2. Approach (chosen)
A. Reuse current JWT Bearer — frontend POSTs JSON {email,password} to /auth/login, gets `{access_token, token_type:"bearer"}`, sends `Authorization: Bearer <token>` per request. Backend decodes, loads user, checks `is_active`. No new deps, stateless.
- Rejected B (OAuth2PasswordBearer form login): nicer Swagger Authorize button, extra plumbing V1 doesn't need.
- Rejected C (session cookies): needs server storage, breaks clean API/mobile use.

## 3. Architecture
- New: `app/schemas/auth.py`, `app/api/deps.py`, `app/api/auth.py`, wired into `app/main.py`.
- Existing untouched: `app/models/user.py`, `app/core/security.py`, `app/core/config.py`, `app/db/session.py`.

## 4. Components
- Schemas:
  - `SignupIn`: name (1-100), email (valid), password (min 8), role (admin|student, default student)
  - `LoginIn`: email, password
  - `TokenOut`: access_token: str, token_type: str = "bearer" — what /login returns
  - `MeOut`: id (UUID), name, email, role — what GET /me returns, never password
- Deps:
  - `get_db` (existing) + `get_current_user`: parse Bearer, `decode_access_token`, load user by sub, 401 if missing/expired, 401 if !is_active
  - `require_admin`: 403 if role != admin; `require_student`: 403 if role != student
- Router `app/api/auth.py`:
  - `POST /auth/signup` → 201 MeOut + creates users row with `hash_password`
  - `POST /auth/login` → 200 TokenOut
  - `GET /me` → 200 MeOut (auth required)
  - `GET /admin/ping` (smoke guard test, admin only)

## 5. Data flow
1. Signup: validate → check email unique → bcrypt hash → insert users(is_active=True) → return MeOut.
2. Login: find by email → `verify_password` → check is_active → `create_access_token(sub=str(user.id))` → return TokenOut.
3. Authed call: header Bearer → decode → SELECT users WHERE id=sub → check is_active → role check → handler.

## 6. Error handling
- 400 email already registered
- 401 invalid credentials, token missing/invalid/expired, user inactive
- 403 insufficient role
- 422 validation (bad email, short password, bad role)
- Never leak which of email/password was wrong beyond generic 401; never return hashed_password.

## 7. Testing
- Happy: signup student → login → /me; signup admin → /admin/ping 200.
- Guards: duplicate signup 400; wrong password 401; no token 401; student → /admin/ping 403; tampered token 401.
- Run: `pytest` + manual `curl` against local Postgres (`DATABASE_URL` in .env.example).

## 8. Scope / non-goals
- No refresh tokens, logout revoke list, password reset, email verification (V2).
- No changes to topics/questions/attempts tables in this step.

## Spec self-review
- Placeholders: none — all fields, routes, codes concrete.
- Consistency: role strings match DB CHECK ('admin','student'); token sub = users.id UUID string matches `decode_access_token -> str`.
- Scope: single slice, fits one implementation plan.
- Ambiguity fixed: TokenOut is login response, MeOut is identity response; expiry from `settings.access_token_expire_minutes`; Bearer header (not cookie).
