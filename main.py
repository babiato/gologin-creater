import logging
import os
import sys
import time

import sqlalchemy as sa
import pathlib

from datetime import date
from concurrent.futures import ProcessPoolExecutor
from sqlalchemy.orm import Session

from automation import Crawler
from api import GoLogin
from models import Proxy, Account

import config


def create_account(num, proxy, sites, suffix):
    api = GoLogin({
        'token': config.TOKEN
    })
    try:
        options = {
            "name": f"{suffix}_{num}",
            "os": "win",
            "proxy_mode": config.PROXY_MODE,
            "proxy_host": f"{proxy.ip.split(':')[0]}",
            "proxy_port": f"{proxy.ip.split(':')[1]}",
            "proxy_username": f"{proxy.login}",
            "proxy_password": f"{proxy.password}"
        }
        profile_id = api.create(options)
    except Exception as e:
        log.exception(e)
        return

    try:
        api.set_profile_id(profile_id)
        debugger_address = api.start()
        crawler = Crawler(debugger_address)
    except Exception as e:
        api.delete(profile_id)
        log.exception(e)
        return

    try:
        crawler.links_opener(sites)
        api.update({
            'notes': 'complite'
        })
    finally:
        while True:
            try:
                crawler.driver.close()
            except Exception:
                break
        api.stop()


def main():
    global log
    if len(sys.argv) != 4:
        log.error("Number of arguments is not correct")
        exit(2)
    log = get_logger()
    suffix = sys.argv[1]
    engine = sa.create_engine(config.DATABASE)
    session = Session(engine)
    f_sites = pathlib.Path("data/sites.txt")
    sites = [site + "\n" for site in f_sites.read_text().split('\n')]
    proxies = session.query(Proxy).where(Proxy.used == 0).all()
    db_num = session.query(sa.func.max(Account.num)).where(Account.date == date.today()).first()[0]
    if not db_num:
        db_num = 0
    nums = range(int(sys.argv[3]), int(sys.argv[2]) + 1)
    with ProcessPoolExecutor(max_workers=config.WORKERS) as executor:
        for num, proxy in zip(nums, proxies):
            executor.submit(create_account, num + db_num, proxy, sites, suffix)
            time.sleep(1)


def get_logger():
    sh = logging.StreamHandler()
    sh.setLevel("DEBUG")
    sh.setFormatter(logging.Formatter(fmt="[{name}]: {message}", style="{"))
    log_filename = f"logs/{date.today():%Y-%m-%d}.log"
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    fh = logging.FileHandler(filename=log_filename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            fmt="[{asctime} {levelname} {name}]: {message}",
            style="{",
            datefmt="%H:%M:%S",
        )
    )
    logging.basicConfig(handlers=[sh, fh])
    log = logging.getLogger("main")
    log.setLevel(logging.DEBUG)
    return log


if __name__ == '__main__':
    main()
