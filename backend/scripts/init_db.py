import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import Base, async_session, engine
from app.core.security import hash_password
from app.models import Organization, Project, User, UserRole
from app.services.demo.iraq_demo_seed import seed_iraq_demo_for_default_project

ROAD_PROJECT = {
    "name": "Road Infrastructure Monitoring",
    "description": "NURAI Dashboard — Iraq road intelligence",
    "domain": "road_infrastructure",
}


async def init_db() -> None:
    settings = get_settings()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        org_result = await db.execute(select(Organization).limit(1))
        org = org_result.scalar_one_or_none()
        if not org:
            org = Organization(name="NURAI Operations")
            db.add(org)
            await db.flush()

        user_result = await db.execute(select(User).where(User.email == settings.admin_email))
        admin = user_result.scalar_one_or_none()
        if not admin:
            admin = User(
                organization_id=org.id,
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                full_name="NURAI Admin",
                role=UserRole.ADMIN,
            )
            db.add(admin)
            await db.flush()
            print(f"Created admin: {settings.admin_email}")

        project_result = await db.execute(
            select(Project).where(Project.name == ROAD_PROJECT["name"], Project.organization_id == org.id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            project = Project(
                organization_id=org.id,
                name=ROAD_PROJECT["name"],
                description=ROAD_PROJECT["description"],
                domain=ROAD_PROJECT["domain"],
            )
            db.add(project)
            await db.flush()
            print(f"Created project: {project.name}")

        await db.commit()

    async with async_session() as db:
        seed_result = await seed_iraq_demo_for_default_project(db)
        if seed_result:
            await db.commit()
            print(f"Demo seed: {seed_result}")


if __name__ == "__main__":
    asyncio.run(init_db())
