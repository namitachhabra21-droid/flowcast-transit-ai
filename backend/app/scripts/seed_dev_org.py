"""Local-dev-only bootstrap: creates an org + admin user + membership + one
API key directly in Postgres, bypassing Clerk entirely. Useful for exercising
the DB/auth/service layer before a real Clerk account is wired up.

Run from backend/: python -m app.scripts.seed_dev_org

Never run this against anything but a local dev database — it manufactures
a fake Clerk identity that would never pass real session verification.
"""
from app.auth.api_key import generate_api_key
from app.db.session import SessionLocal
from app.models import ApiKey, OrgMembership, OrgRole, Organization, PlanTier, User

DEV_ORG_SLUG = "dev-transit-agency"
DEV_CLERK_ORG_ID = "dev_org_local"
DEV_CLERK_USER_ID = "dev_user_local"


def main() -> None:
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.slug == DEV_ORG_SLUG).one_or_none()
        if org is None:
            org = Organization(
                name="Dev Transit Agency",
                slug=DEV_ORG_SLUG,
                clerk_org_id=DEV_CLERK_ORG_ID,
                plan_tier=PlanTier.trial,
            )
            db.add(org)
            db.flush()

        user = db.query(User).filter(User.clerk_user_id == DEV_CLERK_USER_ID).one_or_none()
        if user is None:
            user = User(clerk_user_id=DEV_CLERK_USER_ID, email="dev@example.com", full_name="Dev Admin")
            db.add(user)
            db.flush()

        membership = (
            db.query(OrgMembership)
            .filter(OrgMembership.organization_id == org.id, OrgMembership.user_id == user.id)
            .one_or_none()
        )
        if membership is None:
            db.add(OrgMembership(organization_id=org.id, user_id=user.id, role=OrgRole.admin))

        plaintext, key_prefix, key_hash = generate_api_key()
        db.add(
            ApiKey(
                organization_id=org.id,
                created_by_user_id=user.id,
                name="dev seed key",
                key_prefix=key_prefix,
                key_hash=key_hash,
            )
        )
        db.commit()

        print(f"Organization: {org.name} ({org.id})")
        print(f"Admin user:   {user.email} ({user.id})")
        print(f"API key (shown once, save it): {plaintext}")
        print()
        print("Try it:")
        print(f'  curl -H "X-API-Key: {plaintext}" http://localhost:8000/api/v1/routes')
    finally:
        db.close()


if __name__ == "__main__":
    main()
