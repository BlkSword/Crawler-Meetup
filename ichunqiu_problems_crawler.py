#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import csv
import json
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class IchunqiuProblemsCrawler:

    def __init__(self, url: str, headless: bool = True):
        self.url = url
        self.results = []
        self.driver = None
        self.headless = headless

    def setup_driver(self, driver_path: str = None):
        if driver_path is None:
            driver_path = r"C:\Users\wfshe\.wdm\drivers\chromedriver\143.0.7499.170\chromedriver-win64\chromedriver.exe"

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(3)

    def wait_for_table_load(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'el-table__body'))
            )
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'el-table__row'))
            )
            return True
        except TimeoutException:
            return False

    def parse_table_row(self, row) -> Dict[str, str]:
        cells = row.find_elements(By.TAG_NAME, 'td')
        if len(cells) < 5:
            return None

        try:
            rank_elem = cells[0].find_element(By.CLASS_NAME, 'rank_icon')
            rank = rank_elem.get_attribute('class')
            if 'rank_icon1' in rank:
                ranking = 1
            elif 'rank_icon2' in rank:
                ranking = 2
            elif 'rank_icon3' in rank:
                ranking = 3
            else:
                ranking = rank_elem.text.strip()
        except NoSuchElementException:
            ranking = cells[0].text.strip()

        try:
            team_name = cells[1].find_element(By.CLASS_NAME, 'hand').text.strip()
        except NoSuchElementException:
            team_name = cells[1].text.strip()

        school = cells[2].text.strip()
        total_score = cells[3].text.strip()
        theory_score = cells[4].text.strip()

        return {
            '排名': ranking,
            '队伍名称': team_name,
            '学校/单位名称': school,
            '总分': total_score,
            '理论知识总分': theory_score
        }

    def crawl_current_page(self) -> List[Dict]:
        page_data = []
        try:
            if not self.wait_for_table_load():
                return page_data

            table = self.driver.find_element(By.CLASS_NAME, 'el-table__body')
            rows = table.find_elements(By.TAG_NAME, 'tr')

            for row in rows:
                data = self.parse_table_row(row)
                if data:
                    page_data.append(data)

        except Exception:
            pass

        return page_data

    def get_total_pages(self) -> int:
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'el-pagination'))
            )

            total_elem = self.driver.find_element(By.CLASS_NAME, 'el-pagination__total')
            total_text = total_elem.text
            total_count = int(total_text.replace('共', '').replace('条', '').strip())
            total_pages = (total_count + 9) // 10

            print(f"共 {total_count} 条，{total_pages} 页")
            return total_pages

        except Exception:
            return 1

    def go_to_page(self, page_num: int) -> bool:
        try:
            input_elem = self.driver.find_element(By.CSS_SELECTOR, '.el-pagination__editor input')
            input_elem.clear()
            input_elem.send_keys(str(page_num))
            input_elem.send_keys(Keys.ENTER)
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def init_csv_file(self, filename: str = 'ichunqiu_problems_ranking.csv'):
        fieldnames = ['排名', '队伍名称', '学校/单位名称', '总分', '理论知识总分']
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        self.csv_file = filename

    def append_to_csv(self, data: List[Dict]):
        if not data:
            return
        with open(self.csv_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writerows(data)

    def update_json_file(self, filename: str = 'ichunqiu_problems_ranking.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

    def crawl_all_pages(self, max_pages: int = None, start_page: int = 1, csv_file: str = 'ichunqiu_problems_ranking.csv', json_file: str = 'ichunqiu_problems_ranking.json'):
        self.driver.get(self.url)
        time.sleep(1)

        total_pages = self.get_total_pages()

        if max_pages:
            total_pages = min(total_pages, max_pages)

        self.init_csv_file(csv_file)

        if start_page > 1:
            if not self.go_to_page(start_page):
                return

        for page in range(start_page, total_pages + 1):
            print(f"第 {page}/{total_pages} 页...", end='', flush=True)

            if page != start_page:
                if not self.go_to_page(page):
                    break

            page_data = self.crawl_current_page()
            self.results.extend(page_data)

            if page_data:
                self.append_to_csv(page_data)
                self.update_json_file(json_file)
                print(f" {len(page_data)} 条，累计 {len(self.results)} 条")
            else:
                print(" 0 条")

            time.sleep(0.1)

        print(f"完成！共 {len(self.results)} 条")

    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    url = "https://match.ichunqiu.com/situation/problems?k=VGFVZQ88BmdXMgUyBGBUZgI9AnVbaQdqUz4BPgc0WmxbagI7WmlUOAs9UjBRZw"

    crawler = IchunqiuProblemsCrawler(url, headless=True)

    try:
        crawler.setup_driver()
        crawler.crawl_all_pages(max_pages=None, start_page=1)
    except KeyboardInterrupt:
        print("\n中断")
    except Exception as e:
        print(f"错误: {e}")
    finally:
        crawler.close()


if __name__ == '__main__':
    main()
