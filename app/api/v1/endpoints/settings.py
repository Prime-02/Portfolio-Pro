# from fastapi import APIRouter, Depends
# from app.models.schemas import UserSettings, UserSettingsCreate
# from app.dependencies import get_db

# router = APIRouter(prefix="/settings", tags=["items"])

# @router.post("/", response_model=UserSettings)
# async def create_settings(item: UserSettingsCreate, db=Depends(get_db)):
#     # Your item creation logic here
#     return {"id": 1, **item.dict(), "owner_id": 1}

# @router.get("/{item_id}", response_model=Item)
# async def read_settings(item_id: int):
#     # Your item retrieval logic here
#     return {"id": item_id, "title": "Example", "owner_id": 1}