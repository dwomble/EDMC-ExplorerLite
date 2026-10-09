import json, subprocess
from tests.test_panel import plugin  # noqa
from tests.test_panel import *  # noqa
from explorer.constants import CFG_MINING_COMMODITIES, CFG_MINING_MATERIALS

def test_shot(plugin):
    plugin.load_events("explorer_events.json")
    plugin.play_sequence("honk_only", 0.02)
    st = Context.store
    for i, (pc, vol, mats, dist) in enumerate([("Icy body", "", {"antimony": 1.5, "carbon": 12.0}, 100.0), ("High metal content body", "", {"polonium": 0.8}, 450.0), ("Rocky body", "minor metallic magma volcanism", {}, 900.0)], start=1):
        pk = st.get_or_create_body(explorer_state.cmdr_id, explorer_state.system_id, i, f"QuietSpace A {i}")
        st.update_body(pk, planet_class=pc, volcanism=vol, landable=1, materials=json.dumps(mats), distance_ls=dist, surface_gravity=3.0)
    plugin.config.set(CFG_MINING_COMMODITIES, "Water, Deuterium, Platinum, Olivine, Alexandrite"); plugin.config.set(CFG_MINING_MATERIALS, "Antimony, Polonium")
    Context.panel.refresh()
    root = Context.panel.scroll.interior.winfo_toplevel()
    root.geometry("560x260+80+80"); root.lift(); root.update(); root.update_idletasks()
    import time; time.sleep(0.5); root.update()
    subprocess.run(["screencapture", "-x", "-R80,80,560,260", "/private/tmp/claude-501/-Users-derek-Code-personal/a42291ee-6a99-4466-863d-dc7957aa4984/scratchpad/shot.png"])
