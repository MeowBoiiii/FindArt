
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///bwa.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


exhibition_galleries = Table(
    "exhibition_galleries",
    Base.metadata,
    Column(
        "exhibition_id",
        ForeignKey("exhibitions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "gallery_id",
        ForeignKey("galleries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

exhibition_tags = Table(
    "exhibition_tags",
    Base.metadata,
    Column(
        "exhibition_id",
        ForeignKey("exhibitions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_favorites = Table(
    "user_favorites",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "exhibition_id",
        ForeignKey("exhibitions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
    ),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    favorites = relationship(
        "Exhibition",
        secondary=user_favorites,
        back_populates="favorited_by",
    )


class Gallery(Base):
    __tablename__ = "galleries"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    address = Column(String(500))
    city = Column(String(100))
    website_url = Column(String(1000))

    exhibitions = relationship(
        "Exhibition",
        secondary=exhibition_galleries,
        back_populates="galleries",
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)


class Exhibition(Base):
    __tablename__ = "exhibitions"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    event_type = Column(String(100))
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    description = Column(Text)
    extra_info = Column(Text)
    image_url = Column(String(1000))
    source_url = Column(String(1000), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    galleries = relationship(
        "Gallery",
        secondary=exhibition_galleries,
        back_populates="exhibitions",
    )

    tags = relationship(
        "Tag",
        secondary=exhibition_tags,
    )

    favorited_by = relationship(
        "User",
        secondary=user_favorites,
        back_populates="favorites",
    )


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Baza danych została utworzona.")
