# from sqlalchemy import select, delete
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.models.db_models import User, Notification, UserSettings, UserDevices  # Import all related models
# from app.database import get_db
# import asyncio

# async def delete_users():
#     async for session in get_db():
#         try:
#             # Find users to delete
#             result = await session.execute(
#                 select(User).where(
#                     (User.email == 'utojiubachidera2@gmail.com') | 
#                     (User.username == 'prime-02')
#                 ))
#             users = result.scalars().all()

#             if not users:
#                 print("No matching users found.")
#                 return

#             for user in users:
#                 print(f"Deleting user: {user.username} ({user.email})")
                
#                 # Delete dependent records in proper order (child to parent)
#                 # Start with the most deeply nested relationships first
#                 await session.execute(
#                     delete(Notification).where(Notification.user_id == user.id)
#                 )
#                 await session.execute(
#                     delete(UserDevices).where(UserDevices.user_id == user.id)
#                 )
#                 await session.execute(
#                     delete(UserSettings).where(UserSettings.owner_id == user.id)
#                 )
#                 # Add more delete statements for other dependent tables as needed
                
#                 # Finally delete the user
#                 await session.delete(user)

#             await session.commit()
#             print(f"Successfully deleted {len(users)} user(s) and their related records.")
            
#         except Exception as e:
#             await session.rollback()
#             print(f"An error occurred: {str(e)}")
#             raise
#         finally:
#             await session.close()

# if __name__ == "__main__":
#     asyncio.run(delete_users())




import os
print("DATABASE_URL:", os.getenv("DATABASE_URL"))