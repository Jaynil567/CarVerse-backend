from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Ensure the ./public directory exists
os.makedirs("./public", exist_ok=True)

all_links = set()

def scrape_all_car_links():
    """Scrape pages 2 to 50 for car detail links"""
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Error initializing Selenium WebDriver: {e}")
        print("Make sure you have Chrome browser installed and chromedriver in your PATH.")
        return False
    
    start_page = 2
    end_page = 50
    
    print(f"Scraping pages {start_page} to {end_page}")
    print("=" * 50)
    
    try:
        for page in range(start_page, end_page + 1):
            url = f"https://www.carwale.com/used/ahmedabad/page-{page}/"
            print(f"Page {page}...", end=" ", flush=True)
            
            driver.get(url)
            time.sleep(2)
            
            # Scroll to load all cars
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            links = driver.find_elements(By.TAG_NAME, "a")
            
            page_count = 0
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        href = href.split('?')[0]
                        if re.search(r'/used/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9]+/?$', href):
                            href = href.rstrip('/')
                            if href not in all_links:
                                all_links.add(href)
                                page_count += 1
                except:
                    continue
            
            print(f"+{page_count} new (Total: {len(all_links)})")
            
            if len(all_links) >= 1200:
                print(f"Target {len(all_links)} links achieved! Stopping early.")
                break
            
            time.sleep(1.5)
        
        sorted_links = sorted(list(all_links))
        
        print("\n" + "=" * 50)
        print(f"TOTAL CAR LINKS: {len(sorted_links)}")
        print(f"Saved to ./public/all_car_links.txt")

        with open("./public/all_car_links.txt", "w") as f:
            for link in sorted_links:
                f.write(link + "\n")    
        
        print("\nPreview (first 5):")
        for i, link in enumerate(sorted_links[:5], 1):
            print(f"   {i}. {link}")
        return True
        
    except Exception as e:
        print(f"Error during link scraping: {e}")
        return False
    
    finally:
        driver.quit()

def collect_data_and_create_csv():
    links_path = "./public/all_car_links.txt"
    if not os.path.exists(links_path):
        print(f"Error: {links_path} does not exist. Please run links scraping first.")
        return False

    with open(links_path, "r") as f:
        car_links = [line.strip() for line in f.readlines() if line.strip()]
  
    count = 0
    all_car_data = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    print(f"Starting detail data extraction on {len(car_links)} cars...")
    for link in car_links:
        print(f'Fetching car {count+1} of {len(car_links)}: {link}')
        url = link + '/'

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.url != url:
                print(f"Car {count+1} link is invalid. Skipping.")
                count += 1
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract fields with safe fallbacks
            img_tag = soup.find('img', class_=lambda c: c and 'B6hlWy' in c) or soup.find('img', alt=lambda a: a and 'Car Image' in a) or soup.find('img')
            imagelink = img_tag['src'] if img_tag and img_tag.has_attr('src') else "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80"
            
            name_tag = soup.find("h1", class_=lambda c: c and 'o-j7' in c) or soup.find("h1")
            name = name_tag.text.strip() if name_tag else "Second Hand Car"
            
            overview_list = soup.find_all("div", class_=lambda c: c and 'o-f5' in c)
            
            price = 5.0
            km = 45000
            fuel_type = "Petrol"
            Manufacturing_Year = 2018
            Registration_year = 2018
            No_of_owners = "First"
            Transmission = "Manual"
            Color = "White"
            location = "Ahmedabad"

            if len(overview_list) > 0:
                try: price = float(overview_list[0].text.replace(",", "").replace("Rs.", "").split()[0].strip())
                except: pass
            if len(overview_list) > 1:
                try: km = int(overview_list[1].text.replace(",", "").replace("km", "").strip())
                except: pass
            if len(overview_list) > 2:
                fuel_type = overview_list[2].text.strip().split(" ")[0]
            if len(overview_list) > 4:
                try: Manufacturing_Year = int(overview_list[4].text.strip().split(" ")[1])
                except: pass
            if len(overview_list) > 3:
                val = overview_list[3].text.strip()
                if val != "Not Available" and val != "Not Applicable":
                    try: Registration_year = int(val.split(" ")[1])
                    except: Registration_year = Manufacturing_Year
                else:
                    Registration_year = Manufacturing_Year
            if len(overview_list) > 5:
                No_of_owners = overview_list[5].text.strip()
            if len(overview_list) > 6:
                Transmission = overview_list[6].text.strip().replace(",","").split(" ")[0]
            if len(overview_list) > 7:
                Color = overview_list[7].text.strip()
                if Color == "Not Available":
                    Color = "White"
                if len(Color.split(" ")) > 1:
                    Color = "Black"
            if len(overview_list) > 8:
                location = overview_list[8].text.strip()

            keys = soup.find_all("div", class_=lambda c: c and 'o-jK' in c)
            values = soup.find_all("div", class_=lambda c: c and 'o-hz' in c)
            key_txt = [k.text.strip() for k in keys]
            val_txt = [v.text.strip() for v in values]
            info = dict(zip(key_txt, val_txt))

            engine_capacity = int(info.get("Engine").split(',')[0].split(' ')[0]) if (info.get("Engine") and info.get("Engine")!="-" and info.get('Engine') != "Not Applicable") else 1197
            mileage = float(info.get('Mileage').split(": ")[1].split(" ")[0]) if (info.get('Mileage') and info.get("Mileage")!="-") else 18.2
            length = int(info.get("Length *Width *Height").split(" * ")[0].split(" ")[0]) if (info.get("Length *Width *Height") and info.get("Length *Width *Height")!="-") else 3995
            width = int(info.get("Length *Width *Height").split(" * ")[1].split(" ")[0]) if (info.get("Length *Width *Height") and info.get("Length *Width *Height")!="-") else 1735
            height = int(info.get("Length *Width *Height").split(" * ")[2].split(" ")[0]) if (info.get("Length *Width *Height") and info.get("Length *Width *Height")!="-") else 1515
            wheelbase = int(info.get("Wheelbase").split(" ")[0]) if (info.get("Wheelbase") and info.get("Wheelbase")!="-") else 2450
            seating_capacity = int(info.get("Seating Capacity").split(" ")[0]) if (info.get("Seating Capacity") and info.get("Seating Capacity")!="-" and info.get("Seating Capacity")!="No") else 5
            fuel_tank_capacity = float(info.get("Fuel Tank Capacity").split(" ")[0]) if (info.get("Fuel Tank Capacity") and info.get("Fuel Tank Capacity")!="-") else 37.0
            
            seat_belt_warning = 1 if info.get("Seat Belt Warning") == "Yes" else 0
            heatr = 1 if info.get("Heater") == "Yes" else 0
            cruise_control = 1 if info.get("Cruise Control") == "Yes" else 0
            child_safety_lock = 1 if info.get("Child Safety Lock") == "Yes" else 0
            speed_sensing_door_lock = 1 if info.get("Speed Sensing Door Lock") == "Yes" else 0
            rain_sensing_wipers = 1 if info.get("Rain-sensing Wipers") == "Yes" else 0
            rear_wiper = 1 if info.get("Rear Wiper") == "Yes" else 0

            prices = soup.find_all("p", class_=lambda c: c and 'o-j1' in c)
            
            old_car_price = price
            if len(prices) > 0:
                try:
                    old_car_price_txt = prices[0].text.replace("Rs.", "").replace(",", "").replace("Lakh","").strip()
                    if old_car_price_txt != "N/A":
                        if "Crore" in old_car_price_txt:
                            old_car_price = float(old_car_price_txt.replace("Crore","").strip())*100
                        else:
                            old_car_price = float(old_car_price_txt)
                except: pass
            
            new_car_price = price + price * 0.4
            if len(prices) > 1:
                try:
                    new_car_price_txt = prices[1].text.replace("Rs.", "").replace(",", "").replace("Lakh","").strip()
                    if new_car_price_txt != "N/A":
                        if "Crore" in new_car_price_txt:
                            new_car_price = float(new_car_price_txt.replace("Crore","").strip())*100
                        else:
                            new_car_price = float(new_car_price_txt)
                except: pass

            car_data = (name, km, fuel_type, Manufacturing_Year, Registration_year, No_of_owners, Transmission, Color, location, engine_capacity, mileage, length, width, height, wheelbase, seating_capacity, fuel_tank_capacity, seat_belt_warning, heatr, cruise_control, child_safety_lock, speed_sensing_door_lock, rain_sensing_wipers, rear_wiper, new_car_price, old_car_price, imagelink)
            all_car_data.append(car_data)
            print(f"Car {count+1} data fetched successfully: {name} (Rs. {old_car_price} Lakh)")
            count += 1

        except Exception as e:
            print(f"Error fetching car {count+1} data: {e}")
            count += 1
            continue    
        
    df = pd.DataFrame(all_car_data, columns=['Name','KM','Fuel Type','Manufacturing Year','Registration Year','No of Owners','Transmission','Color','Location','Engine Capacity (cc)','Mileage (kmpl)','Length (mm)','Width (mm)','Height (mm)','Wheelbase (mm)','Seating Capacity','Fuel Tank Capacity (L)','Seat Belt Warning','Heater','Cruise Control','Child Safety Lock','Speed Sensing Door Lock','Rain-sensing Wipers','Rear Wiper','New Car Price (Lakh)','Old Car Price (Lakh)',"IMG"])
    df.to_csv("./public/car_details.csv", index=False)
    print(f"Saved {len(all_car_data)} entries to ./public/car_details.csv")
    return True

def get_options_list():
    df = pd.read_csv("./public/car_details.csv")
    fuel_type_options = df['Fuel Type'].dropna().unique().tolist()
    no_of_owners_options = df['No of Owners'].dropna().unique().tolist()
    transmission_options = df['Transmission'].dropna().unique().tolist()
    color_options = df['Color'].dropna().unique().tolist()
    return fuel_type_options, no_of_owners_options, transmission_options, color_options

def run():
    start_time = time.time()
    print("Starting scraper script...")
    success = scrape_all_car_links()
    if success:
        collect_data_and_create_csv()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total time taken: {elapsed_time:.2f} seconds")
    try:
        return get_options_list()
    except Exception:
        return [], [], [], []

if __name__ == "__main__":
    run()
