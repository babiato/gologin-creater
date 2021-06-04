import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from chromedriver_py import binary_path

import config
import random


class Crawler:
    def __init__(self, debugger_address):
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", debugger_address)
        self.driver = webdriver.Chrome(executable_path=binary_path, options=options)
        try:
            self.allow_popups_windows()
        except Exception as e:
            print(e)

    def allow_popups_windows(self):
        for _ in range(5):
            try:
                self.driver.get("chrome://settings/content/popups")
                site_list_shadow = self.driver.find_element_by_xpath('//settings-ui').get_property(
                    "shadowRoot").find_element_by_id('main').get_property("shadowRoot").find_element_by_css_selector(
                    '[role=main]').get_property("shadowRoot").find_element_by_css_selector(
                    ".expanded > settings-privacy-page").get_property("shadowRoot").find_element_by_css_selector(
                    "settings-subpage[class='iron-selected'] > category-setting-exceptions").get_property(
                    "shadowRoot").find_element_by_css_selector("site-list:last-child").get_property("shadowRoot")

                site_list_shadow.find_element_by_id("addSite").click()
                add_site_dialog_shadow = site_list_shadow.find_element_by_css_selector("add-site-dialog"
                                                                                       ).get_property("shadowRoot")
                input_field = add_site_dialog_shadow.find_element_by_id("site")
                input_field.send_keys("https://apsolyamov.ru")
                add_button = add_site_dialog_shadow.find_element_by_id("add")
                add_button.click()
                break
            except Exception as e:
                time.sleep(2)
                print(e)
        else:
            raise Exception("Fail allow popups")

    def links_opener(self, l_urls):
        self.driver.get("https://apsolyamov.ru/files/url_opener.html")
        l_urls = [l_urls[i * config.NUMBER_OPEN_TABS: (i + 1) * config.NUMBER_OPEN_TABS] for i in
                  range((len(l_urls) + 1) // config.NUMBER_OPEN_TABS)][:random.randrange(
            *config.TOTAL_LINKS) // config.NUMBER_OPEN_TABS]  # Returns a list of links by NUMBER_OPEN_TABS (total random number in the TOTAL_LINKS range
        for urls in l_urls:
            url_field = self.driver.find_element_by_xpath("//textarea")
            url_field.clear()
            url_field.send_keys(*urls)
            self.driver.execute_script("open_all()")
            windows = self.driver.window_handles
            for window in windows[:0:-1]:
                self.driver.switch_to.window(window)
                time.sleep(0.5)
            for window in windows[:0:-1]:  # TODO refactor
                self.driver.switch_to.window(window)
                time.sleep(0.5)
                self.driver.close()
            self.driver.switch_to.window(windows[0])
