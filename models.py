from sqlalchemy import String, DateTime, Column, Integer, create_engine, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StateHistory(Base):
    __tablename__ = 'state_history'
    id = Column(Integer,primary_key=True,autoincrement=True)
    story_id = Column(String(100))
    user_id = Column(String(100))
    state = Column(String(200))
    created_at = Column(DateTime)


class Experience(Base):
    __tablename__ = 'experience'
    id = Column(Integer,primary_key=True,autoincrement=True)
    user_id = Column(String(100))
    story_id = Column(String(100))
    tag = Column(String(100))
    exp = Column(Integer)
    created_at = Column(DateTime)


class PlayerAttribute(Base):
    __tablename__ = 'player_attribute'
    id = Column(Integer,primary_key=True,autoincrement=True)
    user_id = Column(String(100))
    story_id = Column(String(100))
    intelligence = Column(Integer)
    strength = Column(Integer)
    charm = Column(Integer)


class EventHistory(Base):
    __tablename__ = 'event_history'
    id = Column(Integer,primary_key=True,autoincrement=True)
    user_id = Column(String(100))
    story_id = Column(String(100))
    event_id = Column(String(100))
    event_name = Column(String(100))
    chat = Column(String)
    finished = Column(Boolean)
    created_at = Column(DateTime)



engine = create_engine("sqlite:///story.db")
Base.metadata.create_all(engine)
