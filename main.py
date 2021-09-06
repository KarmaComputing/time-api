import requests
import os
from dotenv import load_dotenv
from datetime import date
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

description = "Get time invested"

app = FastAPI(title="Time API", description=description, docs_url="/")

load_dotenv(verbose=True)

API_HOST = os.getenv("API_HOST", "https://app.tmetric.com/api/v3/")
API_TOKEN = os.getenv("API_TOKEN")


class TimeEntries(BaseModel):
    user_id: int
    account_id: int
    date_start: Optional[date] = None
    date_end: Optional[date] = None


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


@app.post("/tmetric-timeentries")
async def read_item(timeEntries: TimeEntries):
    return getTimeEntries(timeEntries)
