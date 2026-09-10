"""Alert management service."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import Alert


async def get_active_alerts(db: AsyncSession, limit: int = 100) -> List[Alert]:
    result = await db.execute(
        select(Alert)
        .where(Alert.acknowledged == False)  # noqa: E712
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def acknowledge_alert(
    db: AsyncSession,
    alert_id: int,
    acknowledged_by: Optional[int] = None,
) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise ValueError(f"Alert {alert_id} not found.")
    alert.acknowledged = True
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert
