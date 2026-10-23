import csv
import os
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "input" / "form_submissions.csv"
OUTPUT_DIR = ROOT / "output"

# Public practice login demo. These credentials are for this demo site only.
LOGIN_URL = "https://practicetestautomation.com/practice-test-login/"
LOGIN_USERNAME = "student"
LOGIN_PASSWORD = "Password123"
LOGIN_SUCCESS_URL_FRAGMENT = "/logged-in-successfully/"

# This is a separate public site; logging in to the first site does not log
# you into QA Academy. The workflow demonstrates login, then navigation.
FORM_URL = "https://jstestingacademy.co.in/qa-demo/forms/practice-form.html"

WAIT_SECONDS = 15
INPUT_DELAY_SECONDS = 2


def create_driver():
    options = Options()
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if os.getenv("HEADLESS", "0").lower() in {"1", "true", "yes"}:
        options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def normalize_header(header):
    return (
        (header or "")
        .replace("\ufeff", "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


ALIASES = {
    "firstname": "firstName",
    "name": "firstName",
    "givenname": "firstName",
    "lastname": "lastName",
    "surname": "lastName",
    "familyname": "lastName",
    "email": "userEmail",
    "useremail": "userEmail",
    "emailaddress": "userEmail",
    "gender": "gender",
    "phone": "userNumber",
    "mobile": "userNumber",
    "mobilenumber": "userNumber",
    "usernumber": "userNumber",
    "state": "state",
    "city": "city",
    "address": "address",
}


def normalize_record(raw_record):
    record = {}
    for key, value in raw_record.items():
        target = ALIASES.get(normalize_header(key))
        if target:
            record[target] = (value or "").strip()

    required = ["firstName", "lastName", "userEmail", "userNumber", "state", "city"]
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ValueError(
            "CSV data is missing required fields: "
            + ", ".join(missing)
            + f". Check the header/data in {INPUT_FILE}"
        )

    record.setdefault("gender", "male")
    record.setdefault("address", "")
    return record


def wait_visible(driver, element_id, timeout=WAIT_SECONDS):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.ID, element_id))
    )


def fill_text(driver, element_id, value):
    field = wait_visible(driver, element_id)
    field.clear()
    field.send_keys(value)
    # Requested pacing: wait two seconds after each text input is filled.
    time.sleep(INPUT_DELAY_SECONDS)


def select_gender(driver, gender):
    gender = gender.strip().lower()
    if gender not in {"male", "female", "other"}:
        raise ValueError(f"Unsupported gender value: {gender!r}")
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.element_to_be_clickable((By.ID, f"gender-{gender}"))
    ).click()
    time.sleep(INPUT_DELAY_SECONDS)


def select_dropdown(driver, element_id, visible_text):
    Select(wait_visible(driver, element_id)).select_by_visible_text(visible_text)
    time.sleep(INPUT_DELAY_SECONDS)


def login_to_practice_site(driver):
    print("Opening practice login page...")
    driver.get(LOGIN_URL)
    fill_text(driver, "username", LOGIN_USERNAME)
    fill_text(driver, "password", LOGIN_PASSWORD)
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.element_to_be_clickable((By.ID, "submit"))
    ).click()

    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.url_contains(LOGIN_SUCCESS_URL_FRAGMENT)
    )
    print("Practice-site login completed.")


def close_result_modal_or_reload(driver):
    selectors = [
        "#result-modal .btn-close",
        "#result-modal button.close",
        "#result-modal [data-bs-dismiss='modal']",
        "#result-modal button",
    ]
    for selector in selectors:
        for button in driver.find_elements(By.CSS_SELECTOR, selector):
            if button.is_displayed() and button.is_enabled():
                button.click()
                try:
                    WebDriverWait(driver, 5).until(
                        EC.invisibility_of_element_located((By.ID, "result-modal"))
                    )
                    return
                except Exception:
                    break

    driver.get(FORM_URL)
    wait_visible(driver, "firstName")


def submit_record(driver, record, record_number):
    result = {
        "record_number": record_number,
        "firstName": record.get("firstName", ""),
        "lastName": record.get("lastName", ""),
        "email": record.get("userEmail", ""),
        "status": "STARTED",
        "message": "",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    try:
        fill_text(driver, "firstName", record["firstName"])
        fill_text(driver, "lastName", record["lastName"])
        fill_text(driver, "userEmail", record["userEmail"])
        select_gender(driver, record["gender"])
        fill_text(driver, "userNumber", record["userNumber"])

        select_dropdown(driver, "state", record["state"])
        WebDriverWait(driver, WAIT_SECONDS).until(
            lambda d: len(Select(d.find_element(By.ID, "city")).options) > 1
        )
        select_dropdown(driver, "city", record["city"])

        if record["address"]:
            address_fields = driver.find_elements(By.ID, "currentAddress")
            if address_fields:
                address_fields[0].clear()
                address_fields[0].send_keys(record["address"])
                time.sleep(INPUT_DELAY_SECONDS)

        WebDriverWait(driver, WAIT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "submit-form"))
        ).click()

        modal = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.visibility_of_element_located((By.ID, "result-modal"))
        )
        result["status"] = "SUBMITTED" if modal.is_displayed() else "UNCONFIRMED"
        result["message"] = modal.text.strip() or "Result modal displayed."
        print(f"Record {record_number}: {result['status']}")
        close_result_modal_or_reload(driver)

    except Exception as exc:
        result["status"] = "ERROR"
        result["message"] = f"{type(exc).__name__}: {exc}"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        screenshot = OUTPUT_DIR / f"error_record_{record_number}.png"
        try:
            driver.save_screenshot(str(screenshot))
            result["message"] += f" | screenshot={screenshot.name}"
        except Exception:
            pass
        print(f"Record {record_number}: ERROR — {type(exc).__name__}: {exc}")

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"CSV not found: {INPUT_FILE}")

    with INPUT_FILE.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        print("CSV headers detected:", reader.fieldnames)
        records = [normalize_record(row) for row in reader]

    if not records:
        print("No form records found in", INPUT_FILE)
        return

    driver = create_driver()
    results = []
    try:
        login_to_practice_site(driver)

        print("Navigating to QA Academy Practice Form...")
        driver.get(FORM_URL)
        wait_visible(driver, "firstName")

        for index, record in enumerate(records, start=1):
            if index > 1:
                driver.get(FORM_URL)
                wait_visible(driver, "firstName")
            results.append(submit_record(driver, record, index))
    finally:
        driver.quit()

    report_path = OUTPUT_DIR / f"rpa_run_{datetime.now():%Y%m%d_%H%M%S}.csv"
    columns = [
        "record_number", "firstName", "lastName", "email",
        "status", "message", "timestamp",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nRPA run complete. Report saved to: {report_path}")


if __name__ == "__main__":
    main()
