# Time api - get time invested

Query time invested via api (using fastapi).

# Usage

https://time.karmacomputing.co.uk/#/default/read_item_tmetric_timeentries_post

Click "Try it out"

Enter your user id and Tmetric account id (same for everyone)

#### how do I find my user id / account id
See example API request image which highlights user id and account id.
https://tmetric.com/help/data-integrations/how-to-use-tmetric-rest-api
# Run locally

```
python3 -m venv venv
pip install -r requirements.txt
. venv/bin/activate
uvicorn main:app --reload
```
Visit http://127.0.0.1:8000
