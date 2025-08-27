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

    rental_daily = st.number_input("Avis daily base rate ($/day)", 0.0, 1000.0, 55.0, step=1.0, key="rental_daily")
    rental_fees_pct = st.number_input("Rental taxes & fees (% of base)", 0.0, 60.0, 22.0, step=0.5, key="rental_fees_pct")
    lodging_nightly = st.number_input("Lodging nightly ($/night)", 0.0, 1000.0, 150.0, step=5.0, key="lodging_nightly")
    lodging_fees_total = st.number_input("One-time lodging fees ($)", 0.0, 1000.0, 60.0, step=5.0, key="lodging_fees_total")
    gas_price = st.number_input("Gas price ($/gal)", 0.0, 10.0, 4.50, step=0.05, key="gas_price")
    mpg = st.number_input("Vehicle MPG", 5.0, 80.0, 30.0, step=0.5, key="mpg")
    park_fee = st.number_input("NPS entrance fee ($ per vehicle)", 0.0, 200.0, 30.0, step=5.0, key="park_fee")
    ferry_total = st.number_input("Estimated ferry total ($ car + driver)", 0.0, 300.0, 50.0, step=1.0, key="ferry_total")




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
    st.write(f"""
**Rental (base):** {usd(b['rental_base'])}  
**Rental (tax/fees):** {usd(b['rental_fees'])}  
**Fuel:** {usd(b['fuel_cost'])}  
**Lodging:** {usd(b['lodging_total'])}  
**Park fee:** {usd(b['park_fee'])}  
**Ferry:** {usd(b['ferry_total'])}
""")

    st.success(f"**Estimated trip total:** {usd(b['total'])}  (≈ {usd(b['per_person'])} per person)")

    st.markdown("---")
    st.subheader("Smart-paste live quotes → auto-fill")
st.caption("Open your Booking/Expedia/Airbnb/Avis page, copy all visible text (Ctrl+A then Ctrl+C), paste below. We'll try to detect prices.")
paste = st.text_area("Paste page text here", height=180, placeholder="Paste anything from the quote page…")

if paste:
    import re
    # Find $ amounts, keep first 10 unique (sorted high→low)
    amounts = re.findall(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)", paste)
    vals = []
    for a in amounts:
        try:
            v = float(a.replace(",", ""))
            if v not in vals:
                vals.append(v)
        except:
            pass
    vals = sorted(vals, reverse=True)[:10]

    if vals:
        st.write("Detected amounts:", vals)
        colx, coly, colz, colw = st.columns(4)
        with colx:
            pick_lodging = st.selectbox("Choose lodging *nightly*", [None] + sorted(vals))
        with coly:
            pick_lodge_fees = st.selectbox("Choose *one-time* lodging fees", [0.0] + sorted(vals))
        with colz:
            pick_avis_daily = st.selectbox("Choose Avis daily", [None] + sorted(vals))
        with colw:
            pick_ferry = st.selectbox("Choose ferry total (optional)", [0.0] + sorted(vals))

        if st.button("Apply selections to sidebar"):
            if pick_lodging is not None:
                st.session_state["lodging_nightly"] = pick_lodging or st.session_state.get("lodging_nightly", 0.0)
            st.session_state["lodging_fees_total"] = pick_lodge_fees
            if pick_avis_daily is not None:
                st.session_state["rental_daily"] = pick_avis_daily or st.session_state.get("rental_daily", 0.0)
            st.session_state["ferry_total"] = pick_ferry
            st.toast("Applied to sidebar. Adjust anything as needed.", icon="✅")
    else:
        st.info("No dollar amounts found. Try copying the page again after prices load, or paste a simpler section.")

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
    st.subheader("Detailed 3-Day Olympic NP Itinerary (veg, no eggs)")

    st.markdown("### Day 1 — Seattle → Port Angeles (base: Port Angeles)")
    st.markdown("""
**06:30–07:00** — Depart Seattle.  
• Ferry: catch 6:45–7:30 Bainbridge sailing.  
• Tacoma route: cross Tacoma by 7:30 to avoid jams.  

**10:30–12:00** — Stop at Lake Crescent. Walk **Marymere Falls** (1.8 mi RT).  
_Carry_: light rain jacket, water, snack bar.  

**12:00–13:00** — Picnic lunch at Lake Crescent (buy in Seattle or Port Angeles).  

**13:30–17:00** — Check into Port Angeles lodging. Rest / explore waterfront.  
Optional: **Olympic Discovery Trail** stroll (flat).  

**18:30** — Dinner: **New Day Eatery** (veg/vegan) or **Next Door Gastropub**.
    """)

    st.markdown("### Day 2 — Port Angeles → Hoh Rain Forest → Beaches (base: Forks/La Push)")
    st.markdown("""
**07:00** — Breakfast in Port Angeles. Pack snacks + water.  
**07:30–10:00** — Drive to Hoh Rain Forest Visitor Center (~2.5 hr).  

**10:00–12:00** — Hike **Hall of Mosses (0.8 mi)** & **Spruce Trail (1.2 mi)**.  
_Carry_: rain jacket, bug spray, water, snacks.  

**12:00–13:00** — Picnic lunch (no restaurants nearby).  

**13:00–15:00** — Drive to Rialto Beach / Second Beach (La Push).  
**15:00–17:00** — Explore tidepools near low tide.  

**Evening** — Overnight in Forks or La Push.  
Dinner: pizza in Forks or Kalaloch Lodge Creekside (veg options).
    """)

    st.markdown("### Day 3 — Forks → Hurricane Ridge → Seattle")
    st.markdown("""
**06:30** — Leave Forks early.  
**09:30–12:00** — **Hurricane Ridge**: short loops (Big Meadow, Cirque Rim).  
_Carry_: jacket (windy), sunscreen, water.  

**12:30–13:30** — Lunch in Port Angeles (cafes / groceries).  

**13:30–16:30** — Drive back to Seattle.  
Traffic tip: avoid Bainbridge ferry after 4 pm weekends; Tacoma route is safer.
    """)

    st.markdown("---")
    st.markdown("#### General Tips")
    st.markdown("""
- **Best bases**: Night 1 — Port Angeles; Night 2 — Forks/La Push.  
- **Traffic**: leave Seattle before 7 am; head back before 1 pm to beat rush.  
- **Food strategy**: Port Angeles/Sequim = best veg eats. Forks = limited. Always pack picnic supplies.  
- **What to carry**: layers, waterproof jacket, sneakers/hiking shoes, refillable water bottles, snacks, sun protection, bug spray, tide chart.
    """)

    c1, c2, c3 = st.columns(3)
    with c1: st.link_button("NPS Fees", "https://www.nps.gov/olym/planyourvisit/fees.htm")
    with c2: st.link_button("Conditions", "https://www.nps.gov/olym/planyourvisit/conditions.htm")
    with c3: st.link_button("La Push Tides", "https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=9442396")

    st.caption("Tip: for strict veg, stock up at Port Angeles/Sequim groceries before heading deeper.")


st.toast("Loaded: compare dates, itinerary, and live‑price link buttons.", icon="✅")
