"""Smoke test: run app.py through streamlit's AppTest framework."""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=120)
at.run()

assert not at.exception, f"App raised an exception: {at.exception}"
print("title      :", at.title[0].value)
print("captions   :", len(at.caption), "captions; first:", at.caption[0].value[:70])
print("metrics    :", [m.label for m in at.metric])
print("values     :", [m.value for m in at.metric])
print("deltas     :", [m.delta for m in at.metric])
print("subheaders :", [s.value for s in at.subheader])
try:
    n_charts = len(at.get("plotly_chart"))
except Exception:
    n_charts = "n/a (custom component)"
print("charts     :", n_charts)
print("sidebar    :", [s.label for s in at.selectbox], at.select_slider[0].label)

# simulate a region filter: APAC -> Oceania
at.selectbox[0].select("APAC")
at.run()
assert not at.exception, f"Exception after selecting APAC: {at.exception}"
at.selectbox[1].select("Oceania")
at.run()
assert not at.exception, f"Exception after selecting Oceania: {at.exception}"
print("\nAPAC/Oceania -> metrics:", [m.value for m in at.metric], [m.delta for m in at.metric])

# year range 2014 only -> delta becomes None (no prior data)
at.select_slider[0].set_value((2014, 2014))
at.run()
assert not at.exception
print("2014 only   -> deltas:", [m.delta for m in at.metric])
print("\nALL CHECKS PASSED")
