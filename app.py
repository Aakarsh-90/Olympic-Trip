import streamlit as st
import datetime as dt
import math
import requests
import pandas as pd

st.set_page_config(page_title="Olympic Trip Optimizer", page_icon="🗺️", layout="wide")

# ---------- helpers ----------
def usd(x):
    try:
        return f"${x:,.0f}"
    except Exception:
        return "—"

def trip_miles(use_ferry: bool, extra: float) -> float:
    base = 360 if use_ferry else 420
    return base + extra

# simple Port Angeles forecast (Open-Meteo)
def forecast_rows(start: dt.date, nights: int):
    try:
        end = start + dt.timedelta(days=int(nights)+1)
        url = (
            "https://api.open-meteo.com/v1/forecast?latitude=48.1181&longitude=-123.4307"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
            f"&start_date={start.isoformat()}&end_date={end.isoformat()}"
        )
        r = requests.get(url, timeout=10)
        d = r.json().get("daily", {})
        rows = []
        for t, tmin, tmax, p in zip(d.get("time", []), d.get("temperature_2m_min", []), d.get("temperature_2m_max", []), d.get("precipitation_probability_max", [])):
            rows.append({"date": t, "min °C": tmin, "max °C": tmax, "precip %": p})
        return rows
    except Exception:
        return []

# deep‑link builders (open in new tab)
BASEDIR = "https://"

def booking_link(city: str, start: dt.date, end: dt.date, adults: int=2):
    return (
        f"https://www.booking.com/searchresults.html?ss={city.replace(' ', '+')}&checkin={start.isoformat()}&checkout={end.isoformat()}&group_adults={adults}&no_rooms=1&order=price"
    )

def expedia_link(city: str, start: dt.date, end: dt.date, adults: int=2):
    return (
        f"https://www.expedia.com/Hotel-Search?destination={city.replace(' ', '%20')}&startDate={start.isoformat()}&endDate={end.isoformat()}&adults={adults}&sort=PRICE_LOW_TO_HIGH"
    )

def airbnb_link(city: str, start: dt.date, end: dt.date, adults: int=2):
    # Basic homes search; adjust filters in the opened page.
    city_q = city.replace(' ', "-")
    return (
        f"https://www.airbnb.com/s/{city_q}/homes?checkin={start.isoformat()}&checkout={end.isoformat()}&adults={adults}"
    )

def avis_location_link(code: str="se2"):
    # se2 = 5th Ave Downtown; r6j = 4th Ave S; se1 = Pike St.
    return f"https://www.avis.com/en/locations/us/wa/seattle/{code}"

# cost math

def cost_breakdown(nights:int, people:int, use_ferry:bool, extra_miles:float,
                   rental_daily:float, rental_fees_pct:float,
                   lodging_nightly:float, lodging_fees_total:float,
                   gas_price:float, mpg:float, park_fee:float, ferry_total:float):
    days = nights + 1  # 2 nights => 3 rental days
    rental_base = rental_daily * days
    rental_fees = rental_base * (rental_fees_pct/100.0)
    miles = trip_miles(use_ferry, extra_miles)
    fuel_cost = (miles/mpg) * gas_price if mpg > 0 else 0
    lodging_total = lodging_nightly * nights + lodging_fees_total
    total = rental_base + rental_fees + fuel_cost + lodging_total + park_fee + (ferry_total if use_ferry else 0)
    per_person = total / people if people else total
    return {
        "rental_base": rental_base,
        "rental_fees": rental_fees,
        "fuel_cost": fuel_cost,
        "lodging_total": lodging_total,
        "park_fee": park_fee,
        "ferry_total": (ferry_total if use_ferry else 0),
        "miles": miles,
        "total": total,
        "per_person": per_person,
    }

st.title("🗺️ Olympic Trip Optimizer — prices & itinerary (free)")

# --- sidebar basics ---
with st.sidebar:
    st.header("Trip basics")
    today = dt.date.today()
    start = st.date_input("Start date", value=today + dt.timedelta(days=14))
    nights = st.number_input("Nights", 2, 10, 2)
    people = st.slider("Travelers", 1, 6, 2)
    use_ferry = st.checkbox("Use Seattle ↔ Bainbridge ferry?", value=True)
    extra_miles = st.number_input("Add extra miles (detours, in-town)", 0.0, 500.0, 40.0, step=5.0)

    st.markdown("---")
    st.header("Costs you control (paste live quotes)")
    st.caption("Enter real numbers you see on Avis / hotel sites for your dates.")
    rental_daily = st.number_input("Avis daily base rate ($/day)", 0.0, 1000.0, 55.0, step=1.0)
    rental_fees_pct = st.number_input("Rental taxes & fees (% of base)", 0.0, 60.0, 22.0, step=0.5)
    lodging_nightly = st.number_input("Lodging nightly ($/night)", 0.0, 1000.0, 150.0, step=5.0)
    lodging_fees_total = st.number_input("One‑time lodging fees ($)", 0.0, 1000.0, 60.0, step=5.0)
    gas_price = st.number_input("Gas price ($/gal)", 0.0, 10.0, 4.50, step=0.05)
    mpg = st.number_input("Vehicle MPG", 5.0, 80.0, 30.0, step=0.5)
    park_fee = st.number_input("NPS entrance fee ($ per vehicle)", 0.0, 200.0, 30.0, step=5.0)
    ferry_total = st.number_input("Estimated ferry total ($ car + driver)", 0.0, 300.0, 50.0, step=1.0)


# --- tabs ---
planner, compare, itinerary = st.tabs(["Cost planner", "Compare dates", "Itinerary & veg eats"])

with planner:
    st.subheader("Route & miles")
    miles = trip_miles(use_ferry, extra_miles)
    c1, c2, c3 = st.columns(3)
    c1.metric("Planned miles", f"{miles:.0f} mi")
    c2.metric("Fuel needed", f"{miles/mpg:.1f} gal")
    c3.metric("Fuel cost", usd((miles/mpg)*gas_price))

    st.subheader("Weather (Port Angeles)")
    rows = forecast_rows(start, nights)
    if rows:
        st.table(pd.DataFrame(rows))
    else:
        st.info("Forecast not available for those dates.")

    st.subheader("Cost breakdown")
    b = cost_breakdown(nights, people, use_ferry, extra_miles,
                       rental_daily, rental_fees_pct, lodging_nightly, lodging_fees_total,
                       gas_price, mpg, park_fee, ferry_total)
    st.write(
        f"**Rental (base):** {usd(b['rental_base'])}  
"
        f"**Rental (tax/fees):** {usd(b['rental_fees'])}  
"
        f"**Fuel:** {usd(b['fuel_cost'])}  
"
        f"**Lodging:** {usd(b['lodging_total'])}  
"
        f"**Park fee:** {usd(b['park_fee'])}  
"
        f"**Ferry:** {usd(b['ferry_total'])}"
    )
    st.success(f"**Estimated trip total:** {usd(b['total'])}  (≈ {usd(b['per_person'])} per person)")

    st.markdown("---")
    st.caption("Quick links to fetch live prices for *your* dates (opens in new tab)")
    city = st.selectbox("Lodging hub", ["Port Angeles, Washington, United States of America", "Sequim, Washington, United States of America", "Forks, Washington, United States of America"]) 
    end = start + dt.timedelta(days=int(nights))
    colA, colB, colC, colD = st.columns(4)
    with colA: st.link_button("Booking.com", booking_link(city, start, end))
    with colB: st.link_button("Expedia", expedia_link(city, start, end))
    with colC: st.link_button("Airbnb", airbnb_link(city, start, end))
    with colD: st.link_button("Avis (5th Ave)", avis_location_link("se2"))
    st.caption("Tip: copy the nightly/total you see and paste into the sidebar fields, then compare below.")

with compare:
    st.subheader("Compare multiple date windows")
    st.caption("Add 2–6 scenarios (midweek vs weekend, different months). Paste the quotes you see from Avis and your hotel/Airbnb.")

    if "scenarios" not in st.session_state:
        dd = dt.date.today()
        st.session_state.scenarios = pd.DataFrame([
            {"label":"Mid‑week Sep (Tue–Thu)", "start": dd.replace(day=min(28, dd.day))+dt.timedelta(days=14), "nights":2,
             "avis_daily":55.0, "avis_fees_pct":22.0, "lodging_nightly":150.0, "lodging_fees":60.0,
             "use_ferry":True, "ferry_total":50.0, "extra_miles":40.0, "gas":4.5, "mpg":30.0, "park_fee":30.0},
            {"label":"Weekend Sep (Fri–Sun)", "start": dd.replace(day=min(28, dd.day))+dt.timedelta(days=16), "nights":2,
             "avis_daily":65.0, "avis_fees_pct":22.0, "lodging_nightly":185.0, "lodging_fees":60.0,
             "use_ferry":False, "ferry_total":0.0, "extra_miles":40.0, "gas":4.6, "mpg":30.0, "park_fee":30.0},
        ])

    df = st.data_editor(
        st.session_state.scenarios,
        num_rows="dynamic",
        column_config={
            "start": st.column_config.DateColumn("Start date"),
            "nights": st.column_config.NumberColumn("Nights", min_value=2, max_value=10, step=1),
            "use_ferry": st.column_config.CheckboxColumn("Ferry?"),
        },
        key="editor",
    )
    st.session_state.scenarios = df

    # compute totals for each row
    results = []
    for _, r in df.iterrows():
        end = r["start"] + dt.timedelta(days=int(r["nights"]))
        b = cost_breakdown(
            nights=int(r["nights"]), people=2, use_ferry=bool(r["use_ferry"]), extra_miles=float(r["extra_miles"]),
            rental_daily=float(r["avis_daily"]), rental_fees_pct=float(r["avis_fees_pct"]),
            lodging_nightly=float(r["lodging_nightly"]), lodging_fees_total=float(r["lodging_fees"]),
            gas_price=float(r["gas"]), mpg=float(r["mpg"]), park_fee=float(r["park_fee"]), ferry_total=float(r["ferry_total"]))
        results.append({
            "label": r["label"],
            "dates": f"{r['start'].strftime('%b %d')} → {(end).strftime('%b %d')}",
            "miles": int(b["miles"]),
            "total": round(b["total"]/1, 0),
            "per_person": round(b["per_person"], 0),
        })
    if results:
        out = pd.DataFrame(results).sort_values("total")
        st.dataframe(out, use_container_width=True)

    st.markdown("**Open searches for a selected row**")
    sel = st.selectbox("Pick a scenario", [r["label"] for r in results] if results else [])
    if sel:
        row = df[df["label"]==sel].iloc[0]
        start2 = row["start"]
        end2 = start2 + dt.timedelta(days=int(row["nights"]))
        city2 = st.selectbox("Lodging hub for this scenario", ["Port Angeles, Washington, United States of America", "Sequim, Washington, United States of America", "Forks, Washington, United States of America"]) 
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.link_button("Booking.com", booking_link(city2, start2, end2))
        with c2: st.link_button("Expedia", expedia_link(city2, start2, end2))
        with c3: st.link_button("Airbnb", airbnb_link(city2, start2, end2))
        with c4: st.link_button("Avis (5th Ave)", avis_location_link("se2"))

with itinerary:
    st.subheader("Easy, relaxing 3‑day plan (veg, no eggs)")
    st.markdown(
        """
### Day 1 – Seattle → Lake Crescent → Port Angeles
- Optional **ferry to Bainbridge** (pretty) or drive via Tacoma (simpler timing).
- **Marymere Falls** (≈1.8 mi RT, mostly easy). Picnic at **Lake Crescent**.
- Check in around Port Angeles; sunset stroll on the waterfront.

### Day 2 – Hoh Rain Forest + Beach (tide‑timed)
- **Hall of Mosses (0.8 mi)** and **Spruce Nature Trail (1.2 mi)** – lush, flat loops.
- Drive to the coast for **Rialto** or **Second Beach** near La Push; go near **low tide**.

### Day 3 – Hurricane Ridge → Seattle
- Short walks at **Hurricane Ridge** (e.g., Big Meadow, Cirque Rim) for alpine views.
- Return via Tacoma if you want to avoid ferry timing.

---
#### Veg/egg‑free eats (always check menus same‑day)
- **Port Angeles:** New Day Eatery (veg/vegan options), Next Door Gastropub (salads, veggie mains), Spruce (seasonal plates). 
- **Sequim:** Nourish (great for special diets), Alder Wood Bistro (seasonal, ask for veg), Sawadee Thai.
- **Forks/nearby:** Simple options like Pacific Pizza or grocery‑store deli; Kalaloch Lodge’s **Creekside Restaurant** lists veg‑friendly items.

#### Handy links
- **NPS Olympic fees & current conditions**
- **WSDOT Seattle ↔ Bainbridge fares**
- **NOAA tides (La Push)**
        """
    )
    c1, c2, c3 = st.columns(3)
    with c1: st.link_button("NPS Fees", "https://www.nps.gov/olym/planyourvisit/fees.htm")
    with c2: st.link_button("Conditions", "https://www.nps.gov/olym/planyourvisit/conditions.htm")
    with c3: st.link_button("La Push Tides", "https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=9442396")

    st.caption("Tip: for strict veg, pack picnic supplies from PA/Sequim groceries. Menus change seasonally.")

st.toast("Loaded: compare dates, itinerary, and live‑price link buttons.", icon="✅")
