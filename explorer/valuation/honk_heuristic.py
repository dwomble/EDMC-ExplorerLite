"""
Honk-only "is a full spectrum scan worth it" heuristic.

Deliberately crude: at honk time (FSSDiscoveryScan) all we know is body count and non-body
signal count -- there's no way to know actual body values without doing the FSS. This is a
starting heuristic, explicitly expected to be revisited/tuned once the plugin sees real use
(see REQUIREMENTS.md's honk-heuristic note) -- not a claim of accuracy.
"""

WORTH_IT_BODY_COUNT = 6
WORTH_IT_NON_BODY_COUNT = 3

def assess(body_count:int, non_body_count:int) -> str:
    """ Return a short (panel-friendly) verdict string. """
    if body_count == 0:
        return "no bodies"
    if body_count >= WORTH_IT_BODY_COUNT or non_body_count >= WORTH_IT_NON_BODY_COUNT:
        return "worth a full scan"
    return "probably quiet"
