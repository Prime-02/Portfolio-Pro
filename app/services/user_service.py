from sqlalchemy.orm import Session

class UserService:
    def __init__(self, db_session: Session):  # Explicit Session type
        self.db = db_session