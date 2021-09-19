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

API_HOST = os.getenv("TMETRIC_API_HOST", "https://app.tmetric.com/api/v3/")
API_TOKEN = os.getenv("TMETRIC_API_TOKEN")

RATE_PER_MIN = float(os.getenv("RATE_PER_MIN"))


class TimeEntries(BaseModel):
    user_id: int
    account_id: int
    startDate: Optional[date] = None
    endDate: Optional[date] = None


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

    startDate = timeEntries.startDate.strftime("%Y-%m-%d")
    endDate = timeEntries.endDate.strftime("%Y-%m-%d")

    api_call = f"{API_HOST}accounts/{ACCOUNT_ID}/timeentries?userId={USER_ID}&startDate={startDate}&endDate={endDate}"  # noqa: E501
    req = requests.get(
        api_call,
        headers=headers,
    )
    return req


def tallyTotalTime(req):
    """Sum all time entries from the given json resp"""

    totalTime = timedelta()
    for entry in req:
        startTime = datetime.strptime(entry["startTime"], "%Y-%m-%dT%H:%M:%S")

        endTime = datetime.strptime(entry["endTime"], "%Y-%m-%dT%H:%M:%S")

        diff = endTime - startTime
        totalTime += diff
    return totalTime


def getTotalUserBillableThisMonth(user_id, account_id):
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
    today = date.today()

    startDate = today.strftime("%Y-%m-1")  # Always first day of current month

    last_day = calendar.monthrange(today.year, int(today.month))[1]

    endDate = today.strftime(f"%Y-%m-{last_day}")
    req = getTimeEntries(
        TimeEntries(
            user_id=user_id,
            account_id=account_id,
            startDate=startDate,
            endDate=endDate,  # noqa: E501
        )
    )
    try:
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return {"error": f"Error fetching time entries: {e}"}

    totalTime = tallyTotalTime(req.json())

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
    user_id: int, account_id: int, month: int, year: int
):  # noqa: E501
    startDate = date(year, month, 1)  # Always from the first date of the month
    last_day = calendar.monthrange(year, month)[1]
    endDate = startDate.strftime(f"%Y-%m-{last_day}")

    req = getTimeEntries(
        TimeEntries(
            user_id=user_id,
            account_id=account_id,
            startDate=startDate,
            endDate=endDate,  # noqa: E501
        )
    )
    totalTime = tallyTotalTime(req.json())

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
        "tmetric_raw": req.json(),
    }


def getTotalBillableThisMonth(user_ids, account_id: int):
    """
    Work out amount billable for all given users combined
    """
    if user_ids is None:
        user_ids = os.getenv("TMETRIC_USER_IDS")
    if account_id is None:
        account_id = os.getenv("TMETRIC_ACCOUNT_ID")

    billablePence = 0
    minutes = 0
    for user_id in user_ids.split(","):
        usersTime = getTotalUserBillableThisMonth(int(user_id), account_id)
        billablePence += usersTime["billable-pennies"]
        minutes += usersTime["totalMinutes"]
    return {
        "totalMinutes": minutes,
        "totalHours": minutes / 60,
        "billable-pounds": billablePence / 100,
        "billable-pennies": billablePence,
        "billable-human-readable": f"£{billablePence / 100}",
        "averageRatePerMin": billablePence / minutes / 100,
    }


def getTotalBillableByMonth(
    user_ids, account_id: int, year: int, month: int
):  # noqa: E501
    """
    Work out amount billable for all given users combined
    """
    if user_ids is None:
        user_ids = os.getenv("TMETRIC_USER_IDS")
    if account_id is None:
        account_id = os.getenv("TMETRIC_ACCOUNT_ID")
    billablePence = 0
    minutes = 0
    for user_id in user_ids.split(","):
        usersTime = getTotalUserBillableByMonth(
            int(user_id), account_id=account_id, month=month, year=year
        )
        billablePence += usersTime["billable-pennies"]
        minutes += usersTime["totalMinutes"]
    return {
        "totalMinutes": minutes,
        "totalHours": minutes / 60,
        "billable-pounds": billablePence / 100,
        "billable-pennies": billablePence,
        "billable-human-readable": f"£{billablePence / 100}",
        "averageRatePerMin": billablePence / minutes / 100,
    }


@app.get("/total-user-billable-this-month")
async def total_user_billable_this_month(user_id: int, account_id: int):
    return getTotalUserBillableThisMonth(user_id, account_id)


@app.get("/total-user-billable-by-month")
async def total_user_billable_by_month(
    user_id: int,
    account_id: int,
    month: int,
    year: Optional[int] = datetime.today().year,
):
    return getTotalUserBillableByMonth(
        user_id, account_id, month=month, year=year
    )  # noqa: E501


@app.get("/total-billable-by-month")
async def total_billable_by_month(
    month: int,
    year: Optional[int] = datetime.today().year,
    account_id: Optional[int] = None,
    user_ids: Optional[str] = None,
):
    return getTotalBillableByMonth(user_ids, account_id, year, month)  # noqa: E501


@app.get("/total-billable-this-month")
async def total_billable_this_month(
    account_id: Optional[int] = None,
    user_ids: Optional[str] = None,
):
    return getTotalBillableThisMonth(user_ids, account_id)  # noqa: E501
