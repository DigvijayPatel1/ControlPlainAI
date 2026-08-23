from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import ChatbotCategory, PrincipalType, SecurityPolicy
from app.models.api_key import ApiKey


#----------------------------------------------------------
# ApiKey repository functions
#----------------------------------------------------------

async def create_api_key(
    db: AsyncSession,
    *,
    principal_id: str,
    principal_type: PrincipalType,
    hashed_secret: str,
    owner_name: str,
    chatbot_category: ChatbotCategory | None = None,
    security_policy: SecurityPolicy = SecurityPolicy.MONITOR,
    entra_object_id: str | None = None,
    expires_at: datetime | None = None,
) -> ApiKey:
    
    key = ApiKey(
        principal_id=principal_id,
        principal_type=principal_type,
        hashed_secret=hashed_secret,
        owner_name=owner_name,
        chatbot_category=chatbot_category,
        security_policy=security_policy,
        entra_object_id=entra_object_id,
        expires_at=expires_at,
    )
    
    db.add(key)
    await db.flush()
    await db.refresh(key)
    
    return key


#----------------------------------------------------------
# ApiKey repository functions
#----------------------------------------------------------

async def get_by_principal_id(
    db: AsyncSession, 
    principal_id: str
) -> ApiKey | None:
    
    result = await db.execute(select(ApiKey).where(ApiKey.principal_id == principal_id))
    return result.scalar_one_or_none()


#----------------------------------------------------------
# ApiKey repository functions
#----------------------------------------------------------

async def get_by_entra_object_id(
    db: AsyncSession, 
    entra_object_id: str
) -> ApiKey | None:
    
    result = await db.execute(
        select(ApiKey).where(ApiKey.entra_object_id == entra_object_id)
    )
    return result.scalar_one_or_none()


#----------------------------------------------------------
# ApiKey repository functions
#----------------------------------------------------------

async def touch_last_used(
    db: AsyncSession, 
    principal_id: str
) -> None:
    
    key = await get_by_principal_id(db, principal_id)
    if key is not None:
        key.last_used_at = datetime.now(timezone.utc)
        await db.flush()


#----------------------------------------------------------
# ApiKey repository functions
#----------------------------------------------------------

async def set_active(
    db: AsyncSession, 
    *, 
    principal_id: str, 
    active: bool
) -> ApiKey | None:
    
    key = await get_by_principal_id(db, principal_id)
    if key is None:
        return None
        
    key.active = active
    
    await db.flush()
    await db.refresh(key)
    
    return key


#----------------------------------------------------------
# ApiKey repository functions
#----------------------------------------------------------

async def update_security_policy(
    db: AsyncSession, 
    *, 
    principal_id: str, 
    security_policy: SecurityPolicy
) -> ApiKey | None:
    
    key = await get_by_principal_id(db, principal_id)
    if key is None:
        return None
        
    key.security_policy = security_policy
    
    await db.flush()
    await db.refresh(key)
    
    return key