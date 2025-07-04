# Airline-Market-Demand-Insight
This Python web app uses the TravelPayouts API to scrape airline booking data, providing real-time insights on price fluctuations, popular routes, and high-demand periods. Users can select origin and destination airports, view price trends, summary statistics (cheapest/most expensive flights), and raw data over multiple months
import os
import io
import base64
from datetime import datetime
from flask import Flask, request, render_template_string
import pandas as pd
import requests
from dotenv import load_dotenv
import matplotlib.pyplot as plt

load_dotenv()

app = Flask(__name__)

TRAVELPAYOUTS_TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN")

if not TRAVELPAYOUTS_TOKEN:
    raise RuntimeError("Missing TRAVELPAYOUTS_TOKEN – add it to the .env file.")

HOSTEL_CITIES = [
    ("SYD", "Sydney"),
    ("MEL", "Melbourne"),
    ("BNE", "Brisbane"),
    ("CNS", "Cairns"),
    ("PER", "Perth"),
]

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Airline Market Demand Insight</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
    <style>
      body {
        background: #f0f4f8;
        font-family: 'Roboto', sans-serif;
      }
      h1, h2, h3 {
        color: #4c4f56;
      }
      .form-label {
        font-weight: 600;
        color: #007bff;
      }
      .form-select, .btn-primary {
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      }
      .form-select:focus, .btn-primary:focus {
        box-shadow: 0 0 10px rgba(0, 123, 255, 0.5);
      }
      .btn-primary {
        background-color: #007bff;
        border-color: #007bff;
        padding: 12px 20px;
        font-weight: bold;
      }
      .btn-primary:hover {
        background-color: #0056b3;
        border-color: #0056b3;
      }
      .result-card {
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
        padding: 20px;
      }
      .result-card h3 {
        margin-bottom: 20px;
      }
      .table {
        margin-top: 30px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      }
      .table th {
        background-color: #007bff;
        color: white;
        text-transform: uppercase;
      }
      .table-striped tbody tr:nth-child(odd) {
        background-color: #f8f9fa;
      }
      .table td, .table th {
        text-align: center;
        padding: 12px;
      }
      .chart-container {
        text-align: center;
        padding: 20px;
        background-color: #ffffff;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      }
      .chart-container img {
        max-height: 300px;
        margin-top: 20px;
      footer {
        color: #6c757d;
        font-size: 14px;
        text-align: center;
        padding: 20px;
        background-color: #ffffff;
        border-top: 2px solid #eeeeee;
        margin-top: 50px;
      }
      .alert {
        border-radius: 8px;
      }
      .alert-danger {
        background-color: #f8d7da;
        color: #721c24;
      }
    </style>
  </head>
  <body>
    <div class="container py-4">
      <h1 class="text-center mb-4">Airline Market Demand Insight</h1>

      <form method="post" class="row g-3 align-items-end">
        <div class="col-sm-4">
          <label class="form-label" for="origin">Origin airport</label>
          <select class="form-select" id="origin" name="origin">{% for code,name in cities %}
            <option value="{{code}}" {% if code==origin %}selected{% endif %}>{{name}} ({{code}})</option>{% endfor %}
          </select>
        </div>
        <div class="col-sm-4">
          <label class="form-label" for="destination">Destination airport</label>
          <select class="form-select" id="destination" name="destination">{% for code,name in cities %}
            <option value="{{code}}" {% if code==destination %}selected{% endif %}>{{name}} ({{code}})</option>{% endfor %}
          </select>
        </div>
        <div class="col-sm-4">
          <button type="submit" class="btn btn-primary w-100">Get Insights</button>
        </div>
      </form>

      {% if error %}
        <div class="alert alert-danger mt-4">{{error}}</div>
      {% endif %}

      {% if summary %}
        <div class="result-card mt-5">
          <h2 class="text-center">Route: {{origin}} → {{destination}}</h2>
          <div class="row my-3">
            <div class="col-md-6">
              <ul class="list-group">
                <li class="list-group-item d-flex justify-content-between"><strong>Average price</strong><span>${{summary.avg_price}}</span></li>
                <li class="list-group-item d-flex justify-content-between"><strong>Cheapest ({{summary.cheapest_date}})</strong><span>${{summary.cheapest_price}}</span></li>
                <li class="list-group-item d-flex justify-content-between"><strong>Most expensive ({{summary.expensive_date}})</strong><span>${{summary.expensive_price}}</span></li>
              </ul>
            </div>
            <div class="col-md-6 chart-container">
              <img src="data:image/png;base64,{{chart_b64}}" class="img-fluid rounded shadow" alt="Price trend" />
            </div>
          </div>
        </div>

        <h3 class="mt-5">Raw Data</h3>
        <div class="table-responsive">
          {{table_html|safe}}
        </div>
      {% endif %}

      <footer>
        Built as a single-file demo – enjoy! 😄
      </footer>
    </div>
  </body>
</html>
"""


def fetch_monthly_prices(origin: str, destination: str) -> pd.DataFrame:
    """Fetches month-level price data from Travelpayouts Monthly Prices API."""
    if not TRAVELPAYOUTS_TOKEN:
        raise RuntimeError("Missing TRAVELPAYOUTS_TOKEN – add it to the .env file.")

    url = "https://api.travelpayouts.com/v1/prices/monthly"
    params = {
        "origin": origin,
        "destination": destination,
        "currency": "AUD",
        "token": TRAVELPAYOUTS_TOKEN
    }

    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"API request failed with status code {resp.status_code}. Message: {resp.text}")

    data = resp.json().get("data", {})

    if not data:
        raise ValueError("API returned empty or invalid data.")

    rows = []
    for month_block in data.values():
        for date_str, price in month_block.items():
            try:
                date = pd.to_datetime(date_str)
                rows.append({"date": date, "price": price})
            except ValueError:
                continue

    df = pd.DataFrame(rows)

    if df.empty or 'date' not in df.columns:
        raise ValueError("No valid date data found in the API response.")

    return df.sort_values("date")


def make_price_plot(df: pd.DataFrame) -> str:
    """Return base64-encoded PNG line chart from DataFrame."""
    fig, ax = plt.subplots()
    ax.plot(df["date"], df["price"], marker="o")
    ax.set_title("Price trend (AUD)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


@app.route("/", methods=["GET", "POST"])
def index():
    origin = request.form.get("origin", "SYD")
    destination = request.form.get("destination", "MEL")
    error = chart_b64 = table_html = None
    summary = {}

    if request.method == "POST":
        try:
            df = fetch_monthly_prices(origin, destination)
            chart_b64 = make_price_plot(df)

            # Calculate summary stats
            summary = {
                "avg_price": df["price"].mean(),
                "cheapest_price": df["price"].min(),
                "cheapest_date": df.loc[df["price"].idxmin()]["date"].strftime("%Y-%m-%d"),
                "expensive_price": df["price"].max(),
                "expensive_date": df.loc[df["price"].idxmax()]["date"].strftime("%Y-%m-%d")
            }

            # Generate HTML table
            table_html = df.to_html(classes="table table-striped")

        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template_string(HTML_TEMPLATE, origin=origin, destination=destination, error=error, summary=summary,
                                  chart_b64=chart_b64, table_html=table_html, cities=HOSTEL_CITIES)


if __name__ == "__main__":
    app.run(debug=True)
