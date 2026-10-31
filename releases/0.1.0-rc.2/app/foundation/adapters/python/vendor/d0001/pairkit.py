"""Small helpers shared by the D0001 pair packages: check records with independent expectations."""
import math
import numpy as np

class Pair:
    def __init__(self, pid, work_type, artifact_modules):
        self.id = pid; self.work_type = work_type; self.modules = list(artifact_modules)
        self.checks = []; self.records = {}; self.status = "complete"; self.integration = "fixture_tested"
        self.spec = {}; self.results = []; self.limitations = []; self.open_issues = []; self.interfaces = {}
        self.unverified_reasons = []; self.iterations = 1; self.repair_log = []
    def check(self, cid, description, expected, observed, ok, kind="independent"):
        self.checks.append({"id": cid, "description": description, "expected": jsonable(expected),
                            "observed": jsonable(observed), "result": "pass" if ok else "fail", "kind": kind})
        return ok
    def unverified(self, cid, description, reason):
        self.checks.append({"id": cid, "description": description, "expected": None, "observed": None,
                            "result": "unverified", "kind": "blocked_prerequisite", "reason": reason})
        self.unverified_reasons.append(reason)
    def raises(self, cid, description, fn, exc):
        try:
            fn(); ok = False; obs = "no exception"
        except exc as e:
            ok = True; obs = "%s: %s" % (type(e).__name__, e)
        except Exception as e:  # wrong exception type is a failure
            ok = False; obs = "unexpected %s: %s" % (type(e).__name__, e)
        return self.check(cid, description, "raises " + exc.__name__, obs, ok)
    def rec(self, key, value): self.records[key] = jsonable(value)

def rnd(x, sig=10):
    if x == 0 or not math.isfinite(x): return float(x)
    return float(f"{x:.{sig}g}")

def jsonable(v):
    if isinstance(v, dict): return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [jsonable(x) for x in v]
    if isinstance(v, np.ndarray): return jsonable(v.tolist())
    if isinstance(v, (np.bool_, bool)): return bool(v)
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        if not math.isfinite(f): return str(f)
        return rnd(f)
    if v is None or isinstance(v, (int, str)): return v
    return str(v)
