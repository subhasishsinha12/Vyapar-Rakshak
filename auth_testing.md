# Auth Testing Playbook (VyaparRakshak AI)

## Step 1 – MongoDB verification
```
mongosh
use vyaparrakshak
db.users.find({role: "owner"}).pretty()
db.users.findOne({email: "owner@vyaparrakshak.in"}, {password_hash: 1})
```
Confirm bcrypt hash starts with `$2b$`. Indexes:
- users.email (unique)
- login_attempts.identifier
- password_reset_tokens.expires_at (TTL)

## Step 2 – API testing
```
curl -c cookies.txt -X POST "$REACT_APP_BACKEND_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@vyaparrakshak.in","password":"Owner@123"}'
cat cookies.txt
curl -b cookies.txt "$REACT_APP_BACKEND_URL/api/auth/me"
```

Login must set `access_token` + `refresh_token` httpOnly cookies. `/me` must return the user via those cookies.

## Step 3 – RBAC
- Maker cannot approve their own payment (409 on final approve).
- Auditor is read-only (POST returns 403).
- Vendor sees only their own vendor profile.
