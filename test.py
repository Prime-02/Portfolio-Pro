from sqlalchemy import select, delete, text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.models.db_models import (
    User,
    Notification,
    UserSettings,
    UserDevices,
)  # Import all related models
from app.database import get_db
import asyncio


async def check_schema_and_list_tables():
    """Check if schema exists and list all tables"""
    async for session in get_db():
        try:
            print("=" * 50)
            print("SCHEMA AND TABLE DISCOVERY")
            print("=" * 50)

            # Get the database engine from the session
            engine = session.get_bind()

            # Create inspector for metadata inspection
            inspector = inspect(engine)

            # Check if we can connect and get basic info
            result = await session.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            print(f"Connected to database: {current_db}")

            # Get schema names (for databases that support schemas like PostgreSQL)
            try:
                result = await session.execute(
                    text("SELECT schema_name FROM information_schema.schemata")
                )
                schemas = [row[0] for row in result.fetchall()]
                print(f"Available schemas: {schemas}")
            except Exception as e:
                print(f"Could not retrieve schemas (might be MySQL/SQLite): {e}")

            # List all tables in the current database/schema
            print("\n" + "-" * 30)
            print("TABLES FOUND:")
            print("-" * 30)

            # Method 1: Using SQLAlchemy inspector
            try:
                table_names = inspector.get_table_names()
                print(f"Tables found via inspector: {len(table_names)}")
                for i, table in enumerate(table_names, 1):
                    print(f"{i:2d}. {table}")
            except Exception as e:
                print(f"Inspector method failed: {e}")

            # Method 2: Using information_schema (works for MySQL, PostgreSQL)
            try:
                result = await session.execute(
                    text(
                        """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() OR table_schema = 'public'
                    ORDER BY table_name
                """
                    )
                )
                info_schema_tables = [row[0] for row in result.fetchall()]
                if info_schema_tables:
                    print(
                        f"\nTables found via information_schema: {len(info_schema_tables)}"
                    )
                    for i, table in enumerate(info_schema_tables, 1):
                        print(f"{i:2d}. {table}")
            except Exception as e:
                print(f"Information_schema method failed: {e}")

            # Method 3: SQLite specific
            try:
                result = await session.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """
                    )
                )
                sqlite_tables = [row[0] for row in result.fetchall()]
                if sqlite_tables:
                    print(f"\nTables found via sqlite_master: {len(sqlite_tables)}")
                    for i, table in enumerate(sqlite_tables, 1):
                        print(f"{i:2d}. {table}")
            except Exception as e:
                print(f"SQLite method failed: {e}")

            return table_names if "table_names" in locals() else []

        except Exception as e:
            print(f"Error during schema discovery: {str(e)}")
            return []
        finally:
            await session.close()


async def get_table_relationships():
    """Get foreign key relationships for better deletion order"""
    async for session in get_db():
        try:
            print("\n" + "=" * 50)
            print("FOREIGN KEY RELATIONSHIPS")
            print("=" * 50)

            # PostgreSQL/MySQL query for foreign keys
            try:
                result = await session.execute(
                    text(
                        """
                    SELECT 
                        tc.table_name as child_table,
                        kcu.column_name as child_column,
                        ccu.table_name as parent_table,
                        ccu.column_name as parent_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    ORDER BY tc.table_name
                """
                    )
                )

                relationships = result.fetchall()
                if relationships:
                    print("Foreign Key Relationships Found:")
                    for rel in relationships:
                        print(f"  {rel[0]}.{rel[1]} -> {rel[2]}.{rel[3]}")
                else:
                    print("No foreign key relationships found via information_schema")

            except Exception as e:
                print(f"Could not retrieve FK relationships: {e}")

        except Exception as e:
            print(f"Error getting relationships: {str(e)}")
        finally:
            await session.close()


async def delete_users():
    """Enhanced user deletion with schema checks"""

    # First, discover schema and tables
    tables = await check_schema_and_list_tables()
    await get_table_relationships()

    async for session in get_db():
        try:
            print("\n" + "=" * 50)
            print("USER DELETION PROCESS")
            print("=" * 50)

            # Find users to delete
            result = await session.execute(
                select(User).where(
                    (User.email == "utojiubachidera2@gmail.com")
                    | (User.username == "prime-02")
                )
            )
            users = result.scalars().all()

            if not users:
                print("No matching users found.")
                return

            print(f"Found {len(users)} user(s) to delete:")
            for user in users:
                print(f"  - {user.username} ({user.email}) - ID: {user.id}")

            # Confirm deletion
            confirm = input("\nProceed with deletion? (yes/no): ")
            if confirm.lower() != "yes":
                print("Deletion cancelled.")
                return

            for user in users:
                print(f"\nDeleting user: {user.username} ({user.email})")

                # Delete dependent records in proper order (child to parent)
                # You can expand this list based on the tables discovered above

                deletion_steps = [
                    (Notification, Notification.user_id, "notifications"),
                    (UserDevices, UserDevices.user_id, "user devices"),
                    (UserSettings, UserSettings.owner_id, "user settings"),
                    # Add more tables here based on your schema discovery
                ]

                for model, foreign_key, description in deletion_steps:
                    try:
                        result = await session.execute(
                            delete(model).where(foreign_key == user.id)
                        )
                        deleted_count = result.rowcount
                        print(f"  - Deleted {deleted_count} {description}")
                    except Exception as e:
                        print(f"  - Warning: Could not delete {description}: {e}")

                # Finally delete the user
                await session.delete(user)
                print(f"  - Deleted user: {user.username}")

            await session.commit()
            print(
                f"\n✅ Successfully deleted {len(users)} user(s) and their related records."
            )

        except Exception as e:
            await session.rollback()
            print(f"❌ An error occurred: {str(e)}")
            raise
        finally:
            await session.close()


async def main():
    """Main function to run the enhanced deletion script"""
    try:
        await delete_users()
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user.")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
