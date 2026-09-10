"""Seed default roles and admin user on first application startup."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.core.logging import logger
from app.models.database_models import User, Role


async def seed_defaults(db: AsyncSession) -> None:
    """Create default roles and admin user if they do not already exist."""
    await _seed_roles(db)
    await _seed_admin(db)


async def _seed_roles(db: AsyncSession) -> None:
    for role_name in ["ADMIN", "SECURITY_ANALYST"]:
        result = await db.execute(select(Role).where(Role.name == role_name))
        if result.scalar_one_or_none() is None:
            db.add(Role(name=role_name, permissions=_default_permissions(role_name)))
            logger.info(f"Seeded role: {role_name}")
    await db.commit()


async def _seed_admin(db: AsyncSession) -> None:
    result = await db.execute(
        select(User).where(User.username == settings.admin_username)
    )
    if result.scalar_one_or_none() is None:
        role_res = await db.execute(select(Role).where(Role.name == "ADMIN"))
        admin_role = role_res.scalar_one_or_none()
        db.add(
            User(
                username=settings.admin_username,
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                role_id=admin_role.id if admin_role else None,
                is_active=True,
            )
        )
        await db.commit()
        logger.info(f"Seeded admin user: {settings.admin_username}")


def _default_permissions(role_name: str) -> dict:
    if role_name == "ADMIN":
        return {"all": True}
    return {
        "read_incidents": True,
        "read_anomalies": True,
        "read_risks": True,
        "read_reports": True,
        "update_incidents": True,
    }
