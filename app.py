import streamlit as st
import datetime as dt
import math
import requests
from typing import List, Tuple

st.set_page_config(page_title="Olympic Trip Optimizer", page_icon="🗺️")

st.title("🗺️ Olympic Trip Optimizer — free & simple")
st.write(
    "Plan a 3‑day (2‑night) Seattle → Olympic National Park trip and estimate *total cost* using only free data sources."
)

with st.sidebar:
    st.header("Trip basics")
    today = dt.date.today()
    start = st.date_input("Start date", value=today + dt.timedelta(days=14))
    nights = st.number_input("Nights", 2, 10, 2)
    people = st.slider("Travelers", 1, 6, 2)
    use_ferry = st.checkbox("Use Seattle ↔ Bainbridge ferry?", value=True)

    st.markdown("---")
    st.header("Costs you control")
    st.caption("Enter the real numbers you see while shopping.")
    rental_daily = st.number_input("Avis daily base rate ($/day)", 0.0, 1000.0, 55.0, step=1.0)
    rental_fees_pct = st.number_input("Rental taxes & fees (% of base)", 0.0, 60.0, 22.0, step=0.5)
    lodging_nightly = st.number_input("Lodging average ($/night)", 0.0, 1000.0, 150.0, step=5.0)
    lodging_fees_total = st.number_input("One‑time lodging fees ($ cleaning, service, etc.)", 0.0, 1000.0, 60.0, step=5.0)
    gas_price = st.number_input("Gas price ($/gal)", 0.0, 10.0, 4.50, step=0.05)
    vehicle_mpg = st.number_input("Vehicle MPG", 5.0, 80.0, 30.0, step=0.5)

st.subheader("Route & miles")
# Reasonable default day-by-day miles for the common loop
# Day1: Seattle → PA + Lake Crescent, Day2: Hoh + Rialto/La Push, Day3: Hurricane Ridge → Seattle
miles_no_ferry = 420  # via Tacoma both ways
miles_with_ferry = 360  # ferry each way reduces driving
base_miles = miles_with_ferry if use_ferry else miles_no_ferry
extra_miles = st.number_input("Add extra miles (detours, in-town)", 0.0, 500.0, 40.0, step=5.0)
trip_miles = base_miles + extra_miles

col1, col2, col3 = st.columns(3)
col1.metric("Planned miles", f"{trip_miles:.0f} mi")
col2.metric("Fuel needed", f"{trip_miles/vehicle_mpg:.1f} gal")
col3.metric("Fuel cost", f"${(trip_miles/vehicle_mpg)*gas_price:,.0f}")

st.subheader("Park fees")
park_fee = 30.0  # NPS private vehicle, 7-day
st.write("Assuming a $30 7‑day private vehicle pass for Olympic (pay once per car). You can adjust below if needed.")
park_fee = st.number_input("NPS entrance fee ($ per vehicle)", 0.0, 200.0, park_fee, step=5.0)

st.subheader("Ferry (optional)")
ferry_roundtrip_vehicle = 0.0
if use_ferry:
    st.caption("Seattle–Bainbridge vehicle fares vary by season and size; check WSDOT for exact pricing and pick one way vs round‑trip as needed.")
    ferry_roundtrip_vehicle = st.number_input("Estimated ferry total ($ car + driver)", 0.0, 300.0, 50.0, step=1.0)

st.subheader("Weather (Open‑Meteo)")
# Fetch simple daily forecast for Port Angeles (48.1181, -123.4307)
try:
    end = start + dt.timedelta(days=int(nights)+1)
    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=48.1181&longitude=-123.4307"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
        f"&start_date={start.isoformat()}&end_date={end.isoformat()}"
    )
    r = requests.get(url, timeout=10)
    data = r.json()
    if "daily" in data:
        daily = data["daily"]
        st.write("**Port Angeles daily forecast**")
        for d, tmin, tmax, p in zip(daily["time"], daily["temperature_2m_min"], daily["temperature_2m_max"], daily["precipitation_probability_max"]):
            st.write(f"{d}: {tmin}–{tmax} °C, precip prob {p}%")
    else:
        st.info("Forecast not available for those dates.")
except Exception as e:
    st.warning("Could not load forecast. Try again later.")

st.subheader("Cost breakdown")
# Rental
rental_base = rental_daily * (nights + 1)  # charge by days; 3 days for 2 nights
rental_fees = rental_base * (rental_fees_pct/100.0)
fuel_cost = (trip_miles/vehicle_mpg) * gas_price
lodging_total = lodging_nightly * nights + lodging_fees_total

ferry_total = ferry_roundtrip_vehicle

total = rental_base + rental_fees + fuel_cost + lodging_total + park_fee + ferry_total
per_person = total / people if people else total

st.write(
    f"**Rental (base):** ${rental_base:,.0f}  \\n**Rental (tax/fees):** ${rental_fees:,.0f}  \
**Fuel:** ${fuel_cost:,.0f}  \
**Lodging:** ${lodging_total:,.0f}  \
**Park fee:** ${park_fee:,.0f}  \
**Ferry:** ${ferry_total:,.0f}"
)

st.success(f"**Estimated trip total:** ${total:,.0f}  (≈ ${per_person:,.0f} per person)")

st.markdown("---")
with st.expander("Suggested easy itinerary (no permit logistics)"):
    st.markdown(
        """
**Day 1 (Seattle → Port Angeles / Lake Crescent)**  
- Optional ferry to Bainbridge, then drive US‑104 → US‑101.  
- Easy stop: Marymere Falls (1.8 mi RT). Picnic at Lake Crescent.

**Day 2 (Hoh Rain Forest + Rialto/Second Beach)**  
- Hall of Mosses (0.8 mi) + Spruce Nature Trail (1.2 mi).  
- Tide‑timed beach walk near La Push (plan around low tide).

**Day 3 (Hurricane Ridge → Seattle)**  
- Short walks at Hurricane Ridge (Cirque Rim, Big Meadow).  
- Drive back via Tacoma (skip ferry if timing is tight).
        """
    )

st.caption("Links: WSDOT Ferries, NPS Olympic Fees/Conditions, NOAA Tides (La Push)")
st.write("- WSDOT Ferries: https://wsdot.wa.gov/travel/washington-state-ferries")
st.write("- NPS Fees: https://www.nps.gov/olym/planyourvisit/fees.htm")
st.write("- NPS Conditions: https://www.nps.gov/olym/planyourvisit/conditions.htm")
st.write("- NOAA Tides (La Push): https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=9442396")

st.markdown(
    """
---
**How to run**  
```bash
pip install streamlit requests
streamlit run app.py
```
**Deploy free** on streamlit.io → New app → connect your repo with this `app.py`.
"""
)
