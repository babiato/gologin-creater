import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import config
from models import Proxy, Base


def make_db(engine):
    Base.metadata.create_all(engine)


def save_to_db(engine):
    session = Session(bind=engine)

    with open("data/proxies.csv", "r", encoding="utf-8") as f_proxies:
        proxies = list(csv.reader(f_proxies, delimiter=":"))
        for file_proxy in proxies:
            if file_proxy:
                file_proxy = [file_proxy[0] + ":" + file_proxy[1], file_proxy[2], file_proxy[3]]  # Maybe change
                if not session.query(Proxy).where(Proxy.ip == file_proxy[0]).first():
                    proxy_execute = Proxy(
                        ip=file_proxy[0],
                        login=file_proxy[1],
                        password=file_proxy[2],
                        used=False
                    )
                    session.add(proxy_execute)
        session.commit()


def main():
    engine = create_engine(config.DATABASE)
    make_db(engine)
    save_to_db(engine)


if __name__ == '__main__':
    main()
