
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Airline Market Demand</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
  <style>
    body {
      background: url('https://images.unsplash.com/photo-1549921296-3c66e1bdfd5d') no-repeat center center fixed;
      background-size: cover;
      font-family: 'Segoe UI', sans-serif;
    }
    .card {
      background-color: rgba(255,255,255,0.95);
      border-radius: 16px;
      padding: 20px;
      margin-top: 40px;
      box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .table th {
      background-color: #007bff;
      color: #fff;
    }
    .chart-container img {
      max-width: 100%;
      border-radius: 12px;
      margin-top: 10px;
    }
    footer {
      margin-top: 60px;
      text-align: center;
      color: #fff;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="text-center text-light mt-4">✈️ Airline Market Demand Insights</h1>
    <form method="POST" class="row g-3 mt-4">
      <div class="col-md-5">
        <label class="form-label text-light">Origin Airport</label>
        <select class="form-select" name="origin">
          {% for code, name in cities %}
            <option value="{{ code }}" {% if code == origin %}selected{% endif %}>{{ name }} ({{ code }})</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-5">
        <label class="form-label text-light">Destination Airport</label>
        <select class="form-select" name="destination">
          {% for code, name in cities %}
            <option value="{{ code }}" {% if code == destination %}selected{% endif %}>{{ name }} ({{ code }})</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2 d-grid">
        <label class="form-label invisible">Submit</label>
        <button type="submit" class="btn btn-primary">Get Insights</button>
      </div>
    </form>

    {% if error %}
    <div class="alert alert-danger mt-4">{{ error }}</div>
    {% endif %}

    {% if summary %}
    <div class="card">
      <h2 class="text-center">Route: {{ origin }} → {{ destination }}</h2>
      <div class="row mt-4">
        <div class="col-md-6">
          <ul class="list-group">
            <li class="list-group-item d-flex justify-content-between"><strong>Average Price</strong><span>${{ summary.avg_price }}</span></li>
            <li class="list-group-item d-flex justify-content-between"><strong>Cheapest ({{ summary.cheapest_date }})</strong><span>${{ summary.cheapest_price }}</span></li>
            <li class="list-group-item d-flex justify-content-between"><strong>Most Expensive ({{ summary.expensive_date }})</strong><span>${{ summary.expensive_price }}</span></li>
          </ul>
        </div>
        <div class="col-md-6 chart-container">
          <img src="data:image/png;base64,{{ chart_b64 }}" alt="Price Trend Chart" />
        </div>
      </div>
    </div>

    <div class="card mt-4">
      <h4>Raw Monthly Price Data</h4>
      <div class="table-responsive">
        {{ table_html|safe }}
      </div>
    </div>
    {% endif %}

    <footer>
      <p>© 2025 Airline Market Demand Web App. Built for assessment.</p>
    </footer>
  </div>
</body>
</html>
"""

def fetch_monthly_prices(origin: str, destination: str) -> pd.DataFrame:
    url = "https://api.travelpayouts.com/v1/prices/monthly"
    params = {
        "origin": origin,
        "destination": destination,
        "currency": "AUD",
        "token": TRAVELPAYOUTS_TOKEN
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")

    data = response.json().get("data", {})
    rows = []

    for month_prices in data.values():
        for date_str, price in month_prices.items():
            try:
                date = pd.to_datetime(date_str)
                rows.append({"date": date, "price": price})
            except Exception:
                continue

    df = pd.DataFrame(rows)
    if df.empty or 'date' not in df.columns:
        raise ValueError("No valid data returned by API.")
    return df.sort_values("date")
def make_price_plot(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots()
    ax.plot(df["date"], df["price"], marker="o", color="#007bff")
    ax.set_title("Monthly Price Trend (AUD)")
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
    error = None
    chart_b64 = table_html = ""
    summary = {}

    if request.method == "POST":
        try:
            df = fetch_monthly_prices(origin, destination)
            chart_b64 = make_price_plot(df)
            summary = {
                "avg_price": round(df["price"].mean(), 2),
                "cheapest_price": df["price"].min(),
                "cheapest_date": df.loc[df["price"].idxmin()]["date"].strftime("%Y-%m-%d"),
                "expensive_price": df["price"].max(),
                "expensive_date": df.loc[df["price"].idxmax()]["date"].strftime("%Y-%m-%d")
            }
            table_html = df.to_html(classes="table table-striped table-bordered", index=False)
        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template_string(
        HTML_TEMPLATE,
        origin=origin,
        destination=destination,
        error=error,
        summary=summary,
        chart_b64=chart_b64,
        table_html=table_html,
        cities=HOSTEL_CITIES
    )
if __name__ == "__main__":
    app.run(debug=True)
