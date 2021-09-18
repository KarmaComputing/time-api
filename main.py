import requests
import os
from dotenv import load_dotenv
from datetime import date, datetime
from datetime import timedelta
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import calendar


description = "Get time invested"

app = FastAPI(title="Time API", description=description, docs_url="/")

load_dotenv(verbose=True)

API_HOST = os.getenv("API_HOST", "https://app.tmetric.com/api/v3/")
API_TOKEN = os.getenv("API_TOKEN")

RATE_PER_MIN = float(os.getenv("RATE_PER_MIN"))


class TimeEntries(BaseModel):
    user_id: int
    account_id: int
    date_start: Optional[date] = None
    date_end: Optional[date] = None


class TmetricAccount(BaseModel):
    user_id: int
    account_id: int


def getTimeEntries(timeEntries: TimeEntries):

    USER_ID = timeEntries.user_id
    ACCOUNT_ID = timeEntries.account_id

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "account": "text/plain",
    }

    startDate = timeEntries.date_start.strftime("%Y-%m-%d")
    endDate = timeEntries.date_end.strftime("%Y-%m-%d")

    api_call = f"{API_HOST}accounts/{ACCOUNT_ID}/timeentries?userId={USER_ID}&startDate={startDate}&endDate={endDate}"  # noqa: E501

    req = requests.get(
        api_call,
        headers=headers,
    )
    return req.json()


def getTotalUserBillableThisMonth(user_id, account_id, rate_per_min=0.75):
    """Calculate the totall billable this month for a user
    return: json
        - The number of minutes invested
        - Number of hours invested
        - Amount billable in smallest unit (e.g. pennies)
        - Amount billable in human readable (e.g. £ and pence)
        {
          "totalHours": 54,
          "totalMinutes": 454,
          "billable": 100,
          "billable-human-readable": "£1",
          "ratePerMin": RATE_PER_MIN,
        }
    """

    USER_ID = user_id
    ACCOUNT_ID = account_id
    totalTime = timedelta()

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "account": "text/plain",
    }

    today = date.today()

    startDate = today.strftime("%Y-%m-1")  # Always first day of current month

    last_day = calendar.monthrange(today.year, int(today.month))[1]

    endDate = today.strftime(f"%Y-%m-{last_day}")

    api_call = f"{API_HOST}accounts/{ACCOUNT_ID}/timeentries?userId={USER_ID}&startDate={startDate}&endDate={endDate}"  # noqa: E501
    try:
        req = requests.get(
            api_call,
            headers=headers,
        )
    except requests.exceptions.ConnectionError as e:
        return f"Connection error to tmetric. {e}"

    resp = req.json()
    for entry in resp:
        startTime = datetime.strptime(entry["startTime"], "%Y-%m-%dT%H:%M:%S")

        endTime = datetime.strptime(entry["endTime"], "%Y-%m-%dT%H:%M:%S")

        diff = endTime - startTime
        totalTime += diff

    def calculateBillable(seconds, ratePerMin):
        return seconds / 60 * RATE_PER_MIN

    billable = calculateBillable(totalTime.total_seconds(), RATE_PER_MIN)
    return {
        "totalMinutes": int(totalTime.total_seconds() / 60),
        "totalHours": totalTime.total_seconds() / 60 / 60,
        "billable-pounds": billable,
        "billable-pennies": int(billable * 100),
        "billable-human-readable": f"£{billable}",
        "ratePerMin": RATE_PER_MIN,
    }


def getTotalUserBillableByMonth(
    user_id: int, account_id: int, rate_per_min: int, month: int, year: int
):
    USER_ID = user_id
    ACCOUNT_ID = account_id
    totalTime = timedelta()

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "account": "text/plain",
    }

    startDate = date(year, month, 1)  # Always from the first date of the month

    last_day = calendar.monthrange(year, month)[1]

    endDate = startDate.strftime(f"%Y-%m-{last_day}")

    api_call = f"{API_HOST}accounts/{ACCOUNT_ID}/timeentries?userId={USER_ID}&startDate={startDate}&endDate={endDate}"  # noqa: E501
    try:
        req = requests.get(
            api_call,
            headers=headers,
        )
    except requests.exceptions.ConnectionError as e:
        return f"Connection error to tmetric. {e}"

    resp = req.json()
    for entry in resp:
        startTime = datetime.strptime(entry["startTime"], "%Y-%m-%dT%H:%M:%S")

        endTime = datetime.strptime(entry["endTime"], "%Y-%m-%dT%H:%M:%S")

        diff = endTime - startTime
        totalTime += diff

    def calculateBillable(seconds, ratePerMin):
        return (seconds / 60) * RATE_PER_MIN

    billable = calculateBillable(totalTime.total_seconds(), RATE_PER_MIN)
    return {
        "totalMinutes": int(totalTime.total_seconds() / 60),
        "totalHours": totalTime.total_seconds() / 60 / 60,
        "billable-pounds": billable,
        "billable-pennies": int(billable * 100),
        "billable-human-readable": f"£{billable}",
        "ratePerMin": RATE_PER_MIN,
        "tmetric_raw": resp,
    }


@app.post("/tmetric-timeentries")
async def read_item(timeEntries: TimeEntries):
    return getTimeEntries(timeEntries)


@app.get("/total-user-billable-this-month")
async def total_user_billable_this_month(
    user_id: int, account_id: int, rate_per_min: Optional[int] = None
):
    return getTotalUserBillableThisMonth(
        user_id, account_id, rate_per_min=rate_per_min
    )  # noqa: E501


@app.get("/total-user-billable-by-month")
async def total_user_billable_by_month(
    user_id: int,
    account_id: int,
    month: int,
    year: Optional[int] = datetime.today().year,
    rate_per_min: Optional[int] = None,
):
    return getTotalUserBillableByMonth(
        user_id, account_id, rate_per_min=rate_per_min, month=month, year=year
    )  # noqa: E501
