import sqlalchemy as sa

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Proxy(Base):
    __tablename__ = "proxy"

    id = sa.Column(sa.Integer, primary_key=True)
    ip = sa.Column(sa.String(256), nullable=False)
    login = sa.Column(sa.String(256), nullable=False)
    password = sa.Column(sa.String(256), nullable=False)
    used = sa.Column(sa.Boolean)


class Account(Base):
    __tablename__ = 'account'
    id = sa.Column(sa.Integer, primary_key=True)
    num = sa.Column(sa.Integer, nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
