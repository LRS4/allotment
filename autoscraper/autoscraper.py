import sys
import re
import time
import datetime
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLineEdit, QTextEdit, QLabel


class ScrapeThread(QThread):
    log_signal = pyqtSignal(str)  # Signal to send log messages to the main thread
    finished_signal = pyqtSignal(list)  # Signal to send the scraped data to the main thread

    def __init__(self, cars, criteria):
        super().__init__()
        self.cars = cars
        self.criteria = criteria

    def run(self):
        data = self.scrape_autotrader(self.cars, self.criteria)
        self.finished_signal.emit(data)

    def scrape_autotrader(self, cars, criteria):
        self.log_signal.emit("Initialising webdriver...")
        service = Service(executable_path=ChromeDriverManager().install()) 
        driver = webdriver.Chrome(service=service)
        data = []

        for car in cars:
            url = "https://www.autotrader.co.uk/car-search?" + \
                  f"advertising-location=at_cars&include-delivery-option=on&" + \
                  f"make={car['make']}&model={car['model']}&postcode={criteria['postcode']}&" + \
                  f"radius={criteria['radius']}&sort=relevance&" + \
                  f"year-from={criteria['year_from']}&year-to={criteria['year_to']}&" + \
                  f"price-from={criteria['price_from']}&price-to={criteria['price_to']}"

            driver.get(url)
            self.log_signal.emit(f"Searching for {car['make']} {car['model']}...")

            time.sleep(5)
            source = driver.page_source
            content = BeautifulSoup(source, "html.parser")

            try:
                pagination_next_element = content.find("a", attrs={"data-testid": "pagination-next"})
                number_of_pages = pagination_next_element.get("aria-label")[-1]
            except:
                self.log_signal.emit("No results found.")
                continue

            self.log_signal.emit(f"There are {number_of_pages} pages in total.")

            for i in range(int(number_of_pages)):
                driver.get(url + f"&page={str(i + 1)}")
                time.sleep(5)
                page_source = driver.page_source
                content = BeautifulSoup(page_source, "html.parser")

                articles = content.findAll("section", attrs={"data-testid": "trader-seller-listing"})
                self.log_signal.emit(f"Scraping page {str(i + 1)}...")

                for article in articles:
                    details = {
                        "name": car['make'] + " " + car['model'],
                        "price": re.search("[£]\d+(\,\d{3})?", article.text).group(0),
                        "year": None,
                        "mileage": None,
                        "transmission": None,
                        "fuel": None,
                        "engine": None,
                        "owners": None,
                        "location": None,
                        "distance": None,
                        "link": article.find("a", {"href": re.compile(r'/car-details/')}).get("href")
                    }

                    try:
                        seller_info = article.find("p", attrs={"data-testid": "search-listing-seller"}).text
                        location = seller_info.split("Dealer location")[1]
                        details["location"] = location.split("(")[0]
                        details["distance"] = location.split("(")[1].replace(" mile)", "").replace(" miles)", "")
                    except:
                        self.log_signal.emit("Seller information not found.")

                    specs_list = article.find("ul", attrs={"data-testid": "search-listing-specs"})
                    for spec in specs_list:
                        if "reg" in spec.text:
                            details["year"] = spec.text

                        if "miles" in spec.text:
                            details["mileage"] = spec.text

                        if spec.text in ["Manual", "Automatic"]:
                            details["transmission"] = spec.text

                        if "." in spec.text and "L" in spec.text:
                            details["engine"] = spec.text

                        if spec.text in ["Petrol", "Diesel"]:
                            details["fuel"] = spec.text

                        if "owner" in spec.text:
                            details["owners"] = spec.text[0]

                    data.append(details)

                self.log_signal.emit(f"Page {str(i + 1)} scraped. ({len(articles)} articles)")
                time.sleep(5)

            self.log_signal.emit("\n\n")

        self.log_signal.emit(f"{len(data)} cars total found.")
        driver.quit()
        return data


class AutoTraderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AutoTrader Search')
        self.setGeometry(100, 100, 800, 600)
        self.initUI()
    
    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()

        # Create input fields for search criteria
        self.postcode_input = QLineEdit(self)
        self.postcode_input.setPlaceholderText('Postcode')
        self.layout.addWidget(self.postcode_input)
        
        self.radius_input = QLineEdit(self)
        self.radius_input.setPlaceholderText('Radius')
        self.layout.addWidget(self.radius_input)
        
        self.year_from_input = QLineEdit(self)
        self.year_from_input.setPlaceholderText('Year From')
        self.layout.addWidget(self.year_from_input)
        
        self.year_to_input = QLineEdit(self)
        self.year_to_input.setPlaceholderText('Year To')
        self.layout.addWidget(self.year_to_input)
        
        self.price_from_input = QLineEdit(self)
        self.price_from_input.setPlaceholderText('Price From')
        self.layout.addWidget(self.price_from_input)
        
        self.price_to_input = QLineEdit(self)
        self.price_to_input.setPlaceholderText('Price To')
        self.layout.addWidget(self.price_to_input)

        # Create input fields for car makes/models
        self.cars_input = QTextEdit(self)
        self.cars_input.setPlaceholderText('Enter cars as JSON (e.g., [{"make": "Toyota", "model": "Yaris"}, ...])')
        self.layout.addWidget(self.cars_input)

        # Create a button to start the search
        self.search_button = QPushButton('Search', self)
        self.search_button.clicked.connect(self.perform_search)
        self.layout.addWidget(self.search_button)
        
        # Create a text area to show results or logs
        self.results_area = QTextEdit(self)
        self.results_area.setReadOnly(True)
        self.layout.addWidget(self.results_area)
        
        self.central_widget.setLayout(self.layout)

    def perform_search(self):
        criteria = {
            "postcode": self.postcode_input.text(),
            "radius": self.radius_input.text(),
            "year_from": self.year_from_input.text(),
            "year_to": self.year_to_input.text(),
            "price_from": self.price_from_input.text(),
            "price_to": self.price_to_input.text(),
        }
        
        try:
            cars = eval(self.cars_input.toPlainText())
            if not isinstance(cars, list):
                raise ValueError("Cars input must be a list of dictionaries.")
        except (SyntaxError, ValueError) as e:
            self.results_area.append(f"Error in cars input: {e}")
            return
        
        self.results_area.append("Starting search...")

        # Start the scraping in a separate thread
        self.scrape_thread = ScrapeThread(cars, criteria)
        self.scrape_thread.log_signal.connect(self.update_log)
        self.scrape_thread.finished_signal.connect(self.output_data_to_excel)
        self.scrape_thread.start()

    def update_log(self, message):
        self.results_area.append(message)

    def output_data_to_excel(self, data):
        df = pd.DataFrame(data)

        df["price"] = df["price"].str.replace("£", "").str.replace(",", "")
        df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("Int64")

        df["year"] = df["year"].str.replace(r"\s(\(\d\d reg\))", "", regex=True)
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

        df["mileage"] = df["mileage"].str.replace(",", "").str.replace(" miles", "")
        df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce").astype("Int64")

        now = datetime.datetime.now()
        df["miles_pa"] = df["mileage"] / (now.year - df["year"])
        df["miles_pa"].fillna(0, inplace=True)
        df["miles_pa"] = df["miles_pa"].astype(int)

        df["owners"] = df["owners"].fillna("-1")
        df["owners"] = df["owners"].astype(int)

        df["distance"] = df["distance"].fillna("-1")
        df["distance"] = df["distance"].astype(int)

        df["link"] = "https://www.autotrader.co.uk" + df["link"]

        df = df[[
            "name",
            "link",
            "price",
            "year",
            "mileage",
            "miles_pa",
            "owners",
            "distance",
            "location",
            "engine",
            "transmission",
            "fuel",
        ]]

        df = df[df["price"] < int(self.price_to_input.text())]
        df = df.sort_values(by="distance", ascending=True)

        writer = pd.ExcelWriter("cars.xlsx", engine="xlsxwriter")
        df.to_excel(writer, sheet_name="Cars", index=False)
        workbook = writer.book
        worksheet = writer.sheets["Cars"]

        worksheet.conditional_format("C2:C1000", {
            'type': '3_color_scale',
            'min_color': '#63be7b',
            'mid_color': '#ffdc81',
            'max_color': '#f96a6c'
        })

        worksheet.conditional_format("D2:D1000", {
            'type': '3_color_scale',
            'min_color': '#f96a6c',
            'mid_color': '#ffdc81',
            'max_color': '#63be7b'
        })

        worksheet.conditional_format("E2:E1000", {
            'type': '3_color_scale',
            'min_color': '#63be7b',
            'mid_color': '#ffdc81',
            'max_color': '#f96a6c'
        })

        worksheet.conditional_format("F2:F1000", {
            'type': '3_color_scale',
            'min_color': '#63be7b',
            'mid_color': '#ffdc81',
            'max_color': '#f96a6c'
        })

        writer.close()

        self.results_area.append("Output saved to 'cars.xlsx'.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutoTraderApp()
    window.show()
    sys.exit(app.exec_())
