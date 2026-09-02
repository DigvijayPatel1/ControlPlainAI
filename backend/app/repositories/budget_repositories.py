from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import PrincipalType
from app.models.budget import Budget


#----------------------------------------------------------
# Budget repository functions
#----------------------------------------------------------

async def create_budget(
    db: AsyncSession,
    *,
    principal_id: str,
    principal_type: PrincipalType,
    monthly_limit_usd: float,
    parent_budget_id: str | None = None,
) -> Budget:
    
    budget = Budget(
        principal_id=principal_id,
        principal_type=principal_type,
        monthly_limit_usd=monthly_limit_usd,
        parent_budget_id=parent_budget_id,
    )
    
    db.add(budget)
    await db.flush()
    await db.refresh(budget)
    
    return budget


#----------------------------------------------------------
# Budget repository functions
#----------------------------------------------------------

async def get_by_principal(
    db: AsyncSession, 
    principal_id: str
) -> Budget | None:
    
    result = await db.execute(select(Budget).where(Budget.principal_id == principal_id))
    return result.scalar_one_or_none()


#----------------------------------------------------------
# Budget repository functions
#----------------------------------------------------------

async def update_limit(
    db: AsyncSession, 
    *, 
    principal_id: str, 
    monthly_limit_usd: float
) -> Budget | None:
    
    budget = await get_by_principal(db, principal_id)
    if budget is None:
        return None
        
    budget.monthly_limit_usd = monthly_limit_usd
    
    await db.flush()
    await db.refresh(budget)
    
    return budget


#----------------------------------------------------------
# Budget repository functions
#----------------------------------------------------------

async def record_usage(
    db: AsyncSession,
    *,
    principal_id: str,
    cost_usd: float,
    was_blocked: bool = False,
) -> Budget | None:
    
    budget = await get_by_principal(db, principal_id)
    if budget is None:
        return None

    budget.spent_usd += cost_usd
    budget.request_count += 1
    
    if was_blocked:
        budget.blocked_count += 1

    await db.flush()
    await db.refresh(budget)
    
    return budget


#----------------------------------------------------------
# Budget repository functions
#----------------------------------------------------------

def is_over_budget(budget: Budget) -> bool:
    
    return budget.spent_usd >= budget.monthly_limit_usd