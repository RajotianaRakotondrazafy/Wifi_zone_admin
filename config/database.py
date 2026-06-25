from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "sqlite:///database/wifi_zone.db"
)

SessionLocal = sessionmaker(bind=engine)