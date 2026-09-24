import asyncio

from app.core.database import close_database, create_tables


async def main() -> None:
    await create_tables()
    await close_database()
    print("Tabelas do PostgreSQL verificadas com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())

