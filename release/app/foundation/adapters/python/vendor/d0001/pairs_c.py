"""Pair packages for the core FrogNano-derived units (C0015, C0064, C0079, C0081, C0085, C0086)."""
import math, statistics
from fractions import Fraction
import numpy as np
from . import frog, frog_sim
from .pairkit import Pair

SRC = {"article": "Uploaded article 'Exhaustive Analysis of Technological Concepts and Modes in Compact Coding Agents.pdf' (catalog sources/article.pdf; image-only, no text layer)",
       "primary": "FrogNano, arXiv 2609.07925v2 (HTML retrieved 2026-10-27)"}
LOC_41 = "arXiv 2609.07925v2 Sec.4.1 Group-Relative Optimization"
LOC_42 = "arXiv 2609.07925v2 Sec.4.2 Efficiency Reward"
LOC_C = "arXiv 2609.07925v2 App.C Merging Checkpoints via Consolidation"

def _spec(p, purpose, definition, locs, contract, assumptions, config, pages):
    p.spec = {"purpose": purpose, "definition": definition, "source_locators": ["%s, pp. %s (catalog citation)" % (SRC["article"], pages)] + locs,
              "contract": contract, "assumptions": assumptions, "configuration": config}

def _ref_drop(A, dp, thr=Fraction(0.2)):
    """Independent expectation: exact rational evaluation of the source rule (strict 'exceeds') against the
    configured threshold value, i.e. the IEEE-754 double nearest 0.2 (declared boundary semantics)."""
    dp = Fraction(dp)
    return (A > 0 and dp > thr) or (A <= 0 and dp < -thr)

# ---------------- C0015 ----------------
def C0015_01():
    p = Pair("C0015-01", "Constraint", ["frog.py", "frog_sim.py"])
    _spec(p, "Divergence-based exclusion of stale/off-policy tokens from the policy-gradient loss.",
          "drop token t iff (A_t>0 and p_t-q_t>0.2) or (A_t<=0 and p_t-q_t<-0.2); strict inequalities ('exceeds')",
          [LOC_41], {"inputs": "A_tok, p (current), q (behaviour) per token, trainable mask (same shape)", "output": "keep mask + reason code per token; ViolationError on malformed input",
                     "enforcement_location": "inside policy_loss, before contributions are summed (every update)"},
          ["A_t=0 is treated with the A<=0 branch (source writes A<=0)", "threshold is the IEEE-754 double 0.2; dp is the float difference p-q; no extra tolerance (a dp that rounds to exactly 0.2 is retained)"],
          {"threshold": 0.2, "strict": True, "violation_behaviour": "reject (raise) for malformed inputs; drop (mask) for rule hits", "empty_set": "explicit zero_signal_all_excluded state, loss 0"}, "3")
    cases = [(+1.0, 0.75, 0.5), (+1.0, 0.45, 0.25), (+1.0, 0.45 + 1e-9, 0.25), (+1.0, 0.1, 0.9), (-1.0, 0.25, 0.45), (-1.0, 0.25 - 1e-9, 0.45),
             (0.0, 0.25, 0.45), (0.0, 0.1, 0.9), (-0.5, 0.9, 0.1), (+0.3, 0.5, 0.5)]
    A = np.array([c[0] for c in cases]); P = np.array([c[1] for c in cases]); Q = np.array([c[2] for c in cases])
    keep, reason = frog.token_selection(A, P, Q, np.ones(len(cases), bool))
    exp = [not _ref_drop(a, pp - qq) for a, pp, qq in cases]
    p.rec("cases", [{"A": a, "p": pp, "q": qq, "dp_float": pp - qq, "kept": bool(k), "reason": str(r)} for (a, pp, qq), k, r in zip(cases, keep, reason)])
    p.check("valid_invalid_boundary_table", "10 hand-built cases incl. dp exactly +-0.2 (float-exact: 0.45-0.25==0.2) and 1e-9 beyond", exp, keep.tolist(), exp == keep.tolist())
    p.check("float_exact_boundary", "0.45-0.25 equals the float 0.2 so the strict boundary is actually exercised", True, (0.45 - 0.25) == 0.2 and (0.25 - 0.45) == -0.2, (0.45 - 0.25) == 0.2)
    p.raises("invalid_q_zero", "behaviour probability q=0 is rejected (rho undefined)", lambda: frog.token_selection(np.ones(1), np.ones(1) * .5, np.zeros(1), np.ones(1, bool)), frog.ViolationError)
    p.raises("invalid_shape", "shape mismatch rejected", lambda: frog.token_selection(np.ones(2), np.ones(3) * .5, np.ones(3) * .5, np.ones(3, bool)), frog.ViolationError)
    out = frog.policy_loss(np.ones(4), np.full(4, 0.9), np.full(4, 0.5), np.ones(4, bool))
    p.check("all_excluded_zero_signal", "all tokens excluded -> explicit zero-signal state, loss 0, |T| unchanged", ["zero_signal_all_excluded", 0.0, 4], [out["state"], out["loss"], out["T"]], out["state"] == "zero_signal_all_excluded" and out["loss"] == 0.0 and out["T"] == 4)
    rng = np.random.default_rng(3); n = 2000; A2 = rng.choice([-1.0, 0.0, 1.0], n); P2 = rng.uniform(0, 1, n); Q2 = rng.uniform(0.01, 1, n)
    k2, _ = frog.token_selection(A2, P2, Q2, np.ones(n, bool)); exp2 = [not _ref_drop(a, Fraction(pp) - Fraction(qq)) for a, pp, qq in zip(A2, P2, Q2)]
    mism = int(sum(int(a) != int(b) for a, b in zip(k2, exp2)))
    p.check("random_agreement_exact_rational", "2000 random tokens: vectorised rule vs exact-rational loop", 0, mism, mism == 0)
    on = frog_sim.token_policy_run(True); off = frog_sim.token_policy_run(False)
    p.rec("enforcement_effect_stale_policy_fixture", {"with_mask": on, "without_mask": off})
    p.check("enforcement_reduces_divergence", "stale-behaviour fixture: max |p-q| over training is lower with the mask", "with < without", [on["max_abs_dp"], off["max_abs_dp"]], on["max_abs_dp"] < off["max_abs_dp"], kind="evaluation")
    p.iterations = 2
    p.repair_log = ["iteration 1: check valid_invalid_boundary_table failed - the independent oracle compared against the exact rational 1/5, while the implementation compares against the configured double 0.2; the float differences 0.45-0.25 and 0.25-0.45 equal +-0.2 exactly, so the oracle (not the implementation) disagreed with the declared boundary semantics", "iteration 2: oracle compares exact rationals against Fraction(0.2) (the configured threshold); boundary semantics recorded in assumptions; all checks pass"]
    p.results = ["Rule implemented with strict inequalities; exact-boundary tokens (dp=+-0.2) are retained.",
                 "Stale-policy toy fixture: max |p-q| %.3f with mask vs %.3f without; kept fraction %.3f." % (on["max_abs_dp"], off["max_abs_dp"], on["mean_kept_fraction"])]
    p.limitations = ["Evaluated on a toy categorical policy, not a coding-agent LLM; no claim about FrogNano training outcomes."]
    p.interfaces = {"producer": "rollout buffer (A_tok from C0015-02, p/q log-probs)", "consumer": "C0064-04 policy_loss"}
    return p

def C0015_02():
    p = Pair("C0015-02", "Loss", ["frog.py", "frog_sim.py"])
    _spec(p, "Group-relative (within-task) reward normalisation producing the advantage.", "A_i=(R_i-mean_g R)/(std_g R+1e-6) over the G trajectories of one task; zero-variance groups dropped",
          [LOC_41], {"inputs": "R (n_groups, G>=2) raw task rewards", "output": "A (same shape), keep[g]"},
          ["std uses ddof=0 (population) - not source-stated", "zero-variance detection is exact (sd>0)"], {"eps": 1e-6, "ddof": 0}, "3")
    R = np.array([[1, 0, 0, 1, 0.5, 0, 1, 0], [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7], [0, 0, 0, 0, 0, 0, 0, 1.0]])
    A, keep = frog.group_advantage(R)
    ref = []
    for row in R.tolist():
        mu = statistics.fmean(row); sd = statistics.pstdev(row); ref.append([(r - mu) / (sd + 1e-6) for r in row] if sd > 0 else [0.0] * len(row))
    err = float(np.max(np.abs(A - np.array(ref))))
    p.check("independent_statistics_module", "advantages vs Python statistics.pstdev loop", "<1e-12", err, err < 1e-12)
    p.check("zero_variance_dropped", "constant-reward group is flagged keep=False", [True, False, True], keep.tolist(), keep.tolist() == [True, False, True])
    p.check("zero_mean_per_group", "sum of advantages in each kept group is 0", "<1e-12", float(np.abs(A[keep].sum(1)).max()), float(np.abs(A[keep].sum(1)).max()) < 1e-12)
    A2, _ = frog.group_advantage(3.0 * R[[0]] + 5.0); d = float(np.abs(A2 - A[[0]]).max())
    p.check("affine_invariance", "A(3R+5) ~= A(R) (scale only enters via eps)", "<1e-5", d, d < 1e-5)
    p.raises("invalid_single_trajectory", "G=1 rejected", lambda: frog.group_advantage(np.ones((2, 1))), frog.ViolationError)
    p.raises("invalid_nan", "non-finite reward rejected", lambda: frog.group_advantage(np.array([[1.0, np.nan]])), frog.ViolationError)
    r = frog_sim.length_policy_run(0.5); p.rec("length_fixture_dropped_groups", r["dropped_groups"])
    p.check("contribution_observable", "zero-variance groups occur and are dropped in the policy fixture (count recorded)", ">0", r["dropped_groups"], r["dropped_groups"] > 0, kind="evaluation")
    p.results = ["Normalisation matches an independent statistics-module computation to <1e-12; zero-variance groups are excluded; %d groups were dropped in the 300-step fixture." % r["dropped_groups"]]
    p.limitations = ["ddof is an assumption; with G=8 the ddof=1 variant would scale A by sqrt(7/8)."]
    p.interfaces = {"producer": "per-task rollout rewards (C0015-03 shaped reward)", "consumer": "C0015-01/C0064 token-level loss via broadcast_advantage"}
    return p

def C0015_03():
    p = Pair("C0015-03", "Loss", ["frog.py", "frog_sim.py"])
    _spec(p, "Success-conditioned logarithmic length penalty (efficiency reward).", "R=1 if n<=N else 1-alpha ln(n/N) for completed successful trajectories; 0.5 truncated-but-correct; 0 otherwise",
          [LOC_42], {"inputs": "success, completed, truncated flags; n assistant tokens; N, alpha", "output": "scalar reward"},
          ["alpha and N are not given in the source - fixture uses N=200, alpha=0.5 (labeled)", "no clipping (source gives none): R may go negative for n > N e^(1/alpha)"],
          {"N": 200, "alpha": 0.5, "boundary": "n==N gets full reward (non-strict)"}, "2-3")
    N, al = 200, 0.5
    cases = [(True, True, False, 150), (True, True, False, 200), (True, True, False, 201), (True, True, False, 400), (False, True, False, 100), (True, False, True, 5000), (False, False, True, 5000), (True, True, False, 2000)]
    obs = [frog.shaped_reward(s, c, t, n, N, al) for s, c, t, n in cases]
    exp = []
    for s, c, t, n in cases:
        exp.append((1.0 if n <= N else 1.0 - al * math.log(n / N)) if (s and c) else (0.5 if (t and s) else 0.0))
    p.check("reward_table_independent", "8 cases incl. n=N, N+1, failure, truncation, negative regime", exp, obs, np.allclose(exp, obs, atol=1e-15))
    p.raises("invalid_truncated_and_completed", "contradictory flags rejected", lambda: frog.shaped_reward(True, True, True, 10, N, al), frog.ViolationError)
    p.raises("invalid_N", "N<=0 rejected", lambda: frog.log_length_adjustment(10, 0, al), frog.ViolationError)
    a5 = frog_sim.length_policy_run(0.5); a0 = frog_sim.length_policy_run(0.0)
    p.rec("ablation", {"alpha_0.5": a5, "alpha_0": a0})
    p.check("contribution_shortens_outputs", "policy fixture: alpha=0.5 yields shorter mean length than alpha=0", "len(0.5) < len(0)", [a5["mean_len"], a0["mean_len"]], a5["mean_len"] < a0["mean_len"], kind="evaluation")
    p.results = ["alpha=0.5: mean length %.0f, success %.3f; alpha=0: mean length %.0f, success %.3f (fixture trade-off, not a FrogNano result)." % (a5["mean_len"], a5["success_rate"], a0["mean_len"], a0["success_rate"])]
    p.limitations = ["alpha/N not source-given; the trade-off depends on the fixture's success-vs-length curve."]
    p.interfaces = {"producer": "C0081/C0085 token count n and success/completion gates", "consumer": "C0015-02 group normalisation"}
    return p

# ---------------- C0064 ----------------
def C0064_01():
    p = Pair("C0064-01", "Constraint", ["frog.py"])
    _spec(p, "Token selection condition K (which trainable tokens enter the loss).", "t in K iff trainable(t) and not [(A>0 and dp>0.2) or (A<=0 and dp<-0.2)]",
          [LOC_41], {"inputs": "A_tok, p, q, trainable", "output": "keep mask"}, ["observation/prompt tokens are never trainable"], {"threshold": 0.2, "strict": True}, "3")
    roles = ["prompt", "reasoning", "text", "observation", "tool_call", "text"]
    A_tok, tr = frog.broadcast_advantage(1.0, roles)
    P = np.array([0.9, 0.9, 0.5, 0.9, 0.45, 0.2]); Q = np.array([0.1, 0.1, 0.5, 0.1, 0.25, 0.8])
    keep, reason = frog.token_selection(A_tok, P, Q, tr)
    exp = [False, False, True, False, True, True]
    p.rec("trace", [{"role": r, "A": a, "p": pp, "q": qq, "keep": bool(k), "reason": str(rs)} for r, a, pp, qq, k, rs in zip(roles, A_tok, P, Q, keep, reason)])
    p.check("role_and_divergence_selection", "masked roles never selected; dp>0.2 with A>0 dropped; boundary dp=0.2 kept", exp, keep.tolist(), keep.tolist() == exp)
    p.check("reason_codes_observable", "every non-kept token carries a reason", ["masked_role", "dp_gt_+thr", "kept", "masked_role", "kept", "kept"], reason.tolist(), reason.tolist() == ["masked_role", "dp_gt_+thr", "kept", "masked_role", "kept", "kept"])
    p.raises("unknown_role", "unknown token role rejected", lambda: frog.broadcast_advantage(1.0, ["system"]), frog.ViolationError)
    out = frog.policy_loss(np.zeros(3), np.full(3, .5), np.full(3, .5), np.zeros(3, bool))
    p.check("no_trainable_tokens", "no trainable tokens -> explicit zero_signal_no_trainable_tokens", "zero_signal_no_trainable_tokens", out["state"], out["state"] == "zero_signal_no_trainable_tokens")
    p.interfaces = {"producer": "broadcast_advantage + rollout log-probs", "consumer": "C0064-02/03/04"}
    p.results = ["Selection predicate combines role masking and the divergence rule; reasons are emitted per token."]
    return p

def C0064_02():
    p = Pair("C0064-02", "Observed signal", ["frog.py"])
    _spec(p, "Retained tokens: the observed learning signal that remains after selection.", "K = T \\ D; contribution_t = -A_t rho_t / |T| for t in K",
          [LOC_41], {"inputs": "token arrays", "output": "per-token contribution aligned with token positions"}, ["contribution is per original token index (alignment preserved)"], {}, "3")
    rng = np.random.default_rng(11); n = 64; A = rng.choice([-1.0, 1.0], n); P = rng.uniform(0.05, 0.95, n); Q = rng.uniform(0.05, 0.95, n); tr = rng.random(n) < 0.8
    out = frog.policy_loss(A, P, Q, tr)
    ref = [(-A[i] * P[i] / Q[i] / tr.sum()) if (tr[i] and not _ref_drop(A[i], Fraction(P[i]) - Fraction(Q[i]))) else 0.0 for i in range(n)]
    err = float(np.max(np.abs(out["contrib"] / tr.sum() - np.array(ref))))
    p.check("alignment_per_token", "retained contribution at each index matches an independent loop", "<1e-12", err, err < 1e-12)
    perm = rng.permutation(n); out2 = frog.policy_loss(A[perm], P[perm], Q[perm], tr[perm])
    p.check("information_boundary_local", "a token's keep decision depends only on its own (A,p,q): permutation-equivariant", True, bool(np.array_equal(out2["keep"], out["keep"][perm])), bool(np.array_equal(out2["keep"], out["keep"][perm])))
    P3 = P.copy(); P3[0] = 0.999; out3 = frog.policy_loss(A, P3, Q, tr)
    same = bool(np.array_equal(out3["keep"][1:], out["keep"][1:]))
    p.check("no_cross_token_leakage", "changing one token's p leaves other tokens' decisions unchanged", True, same, same)
    p.rec("summary", {"T": out["T"], "K": out["K"], "loss": out["loss"]})
    p.results = ["Retained set |K|=%d of |T|=%d trainable tokens; per-token contributions aligned and local." % (out["K"], out["T"])]
    p.interfaces = {"producer": "C0064-01 keep mask", "consumer": "C0064-04 loss sum"}
    return p

def C0064_03():
    p = Pair("C0064-03", "Constraint", ["frog.py"])
    _spec(p, "Excluded tokens contribute nothing to loss or gradient.", "for t in D: contribution_t = 0 and d L / d theta_t = 0", [LOC_41],
          {"inputs": "token arrays", "output": "zero contribution + reason"}, ["exclusion does not shrink the |T| denominator (source: 1/|T| over all trainable tokens)"], {}, "3")
    A = np.array([1.0, 1.0, -1.0, -1.0]); P = np.array([0.9, 0.5, 0.1, 0.5]); Q = np.array([0.5, 0.5, 0.5, 0.5]); tr = np.ones(4, bool)
    out = frog.policy_loss(A, P, Q, tr)
    p.check("excluded_zero_contribution", "tokens 0 (dp=+0.4,A>0) and 2 (dp=-0.4,A<0) contribute exactly 0", [0.0, 0.0], [out["contrib"][0], out["contrib"][2]], out["contrib"][0] == 0.0 and out["contrib"][2] == 0.0)
    h = 1e-7; g = []
    for i in range(4):
        Pp = P.copy(); Pp[i] += h; Pm = P.copy(); Pm[i] -= h
        g.append((frog.policy_loss(A, Pp, Q, tr)["loss"] - frog.policy_loss(A, Pm, Q, tr)["loss"]) / (2 * h))
    p.check("excluded_zero_gradient", "finite-difference dL/dp is 0 for excluded tokens and -A/(q|T|) for kept", [0.0, -1 / (0.5 * 4), 0.0, 1 / (0.5 * 4)], g, abs(g[0]) < 1e-9 and abs(g[2]) < 1e-9 and abs(g[1] + 0.5) < 1e-6 and abs(g[3] - 0.5) < 1e-6)
    p.check("denominator_not_reduced", "|T| stays 4 although 2 tokens are excluded", 4, out["T"], out["T"] == 4)
    p.check("reasons", "excluded tokens carry direction-specific reasons", ["dp_gt_+thr", "kept", "dp_lt_-thr", "kept"], out["reason"].tolist(), out["reason"].tolist() == ["dp_gt_+thr", "kept", "dp_lt_-thr", "kept"])
    p.interfaces = {"producer": "C0064-01", "consumer": "C0064-04 and diagnostics"}
    p.results = ["Excluded tokens have exactly zero loss contribution and zero finite-difference gradient."]
    return p

def C0064_04():
    p = Pair("C0064-04", "Loss", ["frog.py", "frog_sim.py"])
    _spec(p, "Policy loss after exclusion.", "L = -(1/|T|) sum_{t in K} A_t rho_t, rho=p/q; no KL, no entropy bonus", [LOC_41],
          {"inputs": "token arrays", "output": "scalar loss + state"}, ["rho uses probabilities (not clipped; source: exclusion replaces clipping)"], {}, "3")
    rng = np.random.default_rng(5); n = 200; A = rng.normal(size=n); P = rng.uniform(0.05, 0.95, n); Q = rng.uniform(0.05, 0.95, n); tr = rng.random(n) < 0.7
    out = frog.policy_loss(A, P, Q, tr)
    T = int(tr.sum()); s = 0.0
    for i in range(n):
        if tr[i] and not _ref_drop(A[i], Fraction(P[i]) - Fraction(Q[i])): s += -A[i] * P[i] / Q[i]
    p.check("independent_loss", "loss vs explicit loop with exact-rational selection", s / T, out["loss"], abs(s / T - out["loss"]) < 1e-12)
    out0 = frog.policy_loss(A, P, Q, np.zeros(n, bool))
    p.check("empty_T", "|T|=0 returns explicit zero-signal state instead of dividing by 0", "zero_signal_no_trainable_tokens", out0["state"], out0["state"] == "zero_signal_no_trainable_tokens")
    on = frog_sim.token_policy_run(True); off = frog_sim.token_policy_run(False)
    p.rec("contribution", {"with_exclusion": on, "without_exclusion": off})
    p.check("contribution_evaluated", "loss with exclusion still learns the target token in the fixture (p_target>0.9)", ">0.9", on["final_p_target"], on["final_p_target"] > 0.9, kind="evaluation")
    p.results = ["Loss equals an independent computation; with exclusion the fixture still learns (p_target=%.3f) while bounding divergence." % on["final_p_target"]]
    p.interfaces = {"producer": "C0064-01..03", "consumer": "optimizer step (fixture)"}
    return p

# ---------------- C0079 ----------------
def _ref_logits(V=256, seed=0): return np.random.default_rng(seed).normal(0, 3, V)

def C0079_01():
    p = Pair("C0079-01", "Representation", ["frog.py"])
    _spec(p, "Reference-model logits used as the consolidation target.", "per position, a finite logit vector over the shared vocabulary from the frozen reference model", [LOC_C],
          {"inputs": "reference logits (V,)", "output": "validated vector, top-k indices"}, ["reference model replaced by a seeded fixture vector (no model weights available)"], {"V": 256}, "5")
    z = _ref_logits(); sm = frog.softmax(z)
    p.check("softmax_normalised", "softmax of reference logits sums to 1", 1.0, float(sm.sum()), abs(sm.sum() - 1) < 1e-12)
    p.check("shift_invariance", "softmax(z+c)==softmax(z) (logit identity)", "<1e-15", float(np.abs(frog.softmax(z + 100) - sm).max()), float(np.abs(frog.softmax(z + 100) - sm).max()) < 1e-12)
    p.raises("invalid_nonfinite", "NaN logits rejected", lambda: frog.reference_topk(np.array([0.0, np.nan]), 1), frog.ViolationError)
    p.raises("invalid_2d", "matrix passed where a vector is required", lambda: frog.reference_topk(np.zeros((2, 2)), 1), frog.ViolationError)
    p.raises("vocab_mismatch", "student/reference vocabulary mismatch rejected", lambda: frog.consolidation_loss(np.zeros(10), np.zeros(11), 0, 5), frog.ViolationError)
    p.integration = "fixture_tested"; p.limitations = ["No reference checkpoint: structural properties only."]
    p.interfaces = {"producer": "frozen reference model (fixture)", "consumer": "C0079-02/03/04"}
    p.results = ["Reference-logit representation validated for normalisation, invariance and shape contracts."]
    return p

def C0079_02():
    p = Pair("C0079-02", "Parameter", ["frog.py"])
    _spec(p, "Top-64 support size for the consolidation KL.", "k=64 largest reference logits", [LOC_C], {"inputs": "k", "output": "indices"}, ["ties broken by lower index (deterministic)"], {"TOPK": frog.TOPK}, "5")
    p.check("central_config", "single constant frog.TOPK used by default", 64, frog.TOPK, frog.TOPK == 64)
    z = _ref_logits(); idx = frog.reference_topk(z)
    ref = sorted(range(z.size), key=lambda i: (-z[i], i))[:64]
    p.check("topk_independent", "indices equal a sorted() reference", ref, idx.tolist(), idx.tolist() == ref)
    zt = np.zeros(100); zt[[3, 7, 9]] = 1.0
    p.check("deterministic_ties", "ties resolved by lower index", [3, 7], frog.reference_topk(zt, 2).tolist(), frog.reference_topk(zt, 2).tolist() == [3, 7])
    p.check("boundary_k_equals_V", "k=V allowed", 256, int(frog.reference_topk(z, 256).size), frog.reference_topk(z, 256).size == 256)
    p.raises("k_gt_V", "k > vocabulary rejected", lambda: frog.reference_topk(np.zeros(10)), frog.ViolationError)
    p.raises("k_zero", "k=0 rejected", lambda: frog.reference_topk(z, 0), frog.ViolationError)
    p.interfaces = {"producer": "configuration", "consumer": "C0079-04"}; p.results = ["k=64 central, validated against vocabulary size; deterministic tie-breaking."]
    return p

def C0079_03():
    p = Pair("C0079-03", "Constraint", ["frog.py"])
    _spec(p, "Target/reference agreement condition selecting the KL branch.", "agree iff target token id == argmax reference logits (top-1)", [LOC_C],
          {"inputs": "target id, reference logits", "output": "bool / branch"}, ["ties at top-1 resolved by lower index"], {}, "5")
    z = _ref_logits(); top = int(np.argmax(z)); other = (top + 1) % z.size
    p.check("agree_valid", "target==top-1 -> topk_kl branch", "topk_kl", frog.consolidation_loss(np.zeros_like(z), z, top)["branch"], frog.consolidation_loss(np.zeros_like(z), z, top)["branch"] == "topk_kl")
    p.check("disagree", "target!=top-1 -> cross_entropy branch", "cross_entropy", frog.consolidation_loss(np.zeros_like(z), z, other)["branch"], frog.consolidation_loss(np.zeros_like(z), z, other)["branch"] == "cross_entropy")
    zt = np.zeros(70); zt[[4, 5]] = 2.0
    p.check("tie_boundary", "tied maxima: lowest index counts as top-1", [True, False], [frog.agreement(4, zt), frog.agreement(5, zt)], frog.agreement(4, zt) and not frog.agreement(5, zt))
    p.raises("target_out_of_range", "target id outside vocab rejected", lambda: frog.consolidation_loss(np.zeros(70), zt, 70), frog.ViolationError)
    p.interfaces = {"producer": "C0079-01/02", "consumer": "C0079-04 branch selection"}; p.results = ["Agreement predicate validated incl. ties and out-of-range targets."]
    return p

def C0079_04():
    p = Pair("C0079-04", "Loss", ["frog.py", "frog_sim.py"])
    _spec(p, "KL consolidation loss on top-64 logits.", "agree: KL(p_ref^64 || p_student^64) on reference top-64 (renormalised); else CE on target", [LOC_C],
          {"inputs": "student logits, reference logits, target", "output": "loss, branch, gradient"}, ["KL direction ref||student and renormalisation over the 64 indices are assumptions"], {"k": 64}, "5")
    rng = np.random.default_rng(2); z = _ref_logits(); s = rng.normal(size=z.size); top = int(np.argmax(z))
    out = frog.consolidation_loss(s, z, top); idx = sorted(range(z.size), key=lambda i: (-z[i], i))[:64]
    pr = [math.exp(z[i]) for i in idx]; ps = [math.exp(s[i]) for i in idx]; Zr = sum(pr); Zs = sum(ps)
    kl = sum((a / Zr) * math.log((a / Zr) / (b / Zs)) for a, b in zip(pr, ps))
    p.check("kl_independent", "KL vs math-module loop", kl, out["loss"], abs(kl - out["loss"]) < 1e-10)
    p.check("kl_zero_at_match", "student==reference -> KL=0", 0.0, frog.consolidation_loss(z.copy(), z, top)["loss"], abs(frog.consolidation_loss(z.copy(), z, top)["loss"]) < 1e-12)
    g = frog.consolidation_grad(s, z, top); h = 1e-6; fd = []
    for j in [idx[0], idx[10], int(np.argmin(z))]:
        sp = s.copy(); sp[j] += h; sm_ = s.copy(); sm_[j] -= h
        fd.append((frog.consolidation_loss(sp, z, top)["loss"] - frog.consolidation_loss(sm_, z, top)["loss"]) / (2 * h))
    p.check("gradient_fd", "analytic gradient vs central differences (incl. an index outside top-64 -> 0)", fd, [g[idx[0]], g[idx[10]], g[int(np.argmin(z))]], np.allclose(fd, [g[idx[0]], g[idx[10]], g[int(np.argmin(z))]], atol=1e-6))
    a = frog_sim.consolidation_run("topk"); b = frog_sim.consolidation_run("ce_only")
    p.rec("contribution", {"topk_rule": a, "ce_only": b})
    p.check("contribution_evaluated", "full-vocab KL to reference on agreeing contexts is lower with the top-64 rule than CE-only", "topk < ce_only", [a["mean_full_vocab_kl_on_agree"], b["mean_full_vocab_kl_on_agree"]], a["mean_full_vocab_kl_on_agree"] < b["mean_full_vocab_kl_on_agree"], kind="evaluation")
    p.results = ["Top-64 KL matches an independent loop; fixture: full-vocab KL %.2f (top-64 rule) vs %.2f (CE only), top-1 match %.2f vs %.2f." % (a["mean_full_vocab_kl_on_agree"], b["mean_full_vocab_kl_on_agree"], a["top1_match_on_agree"], b["top1_match_on_agree"])]
    p.interfaces = {"producer": "C0079-01..03", "consumer": "consolidation optimiser (fixture)"}
    return p

# ---------------- C0081 / C0085 / C0086 (length accounting) ----------------
def _gate_pair(pid, locpages, seed):
    p = Pair(pid, "Constraint", ["frog.py"])
    _spec(p, "Successful-completion gate for the length penalty.", "penalty branch applies iff success AND completed (not truncated)", [LOC_42],
          {"inputs": "success, completed (bool)", "output": "bool"}, ["non-bool inputs are rejected rather than coerced"], {}, locpages)
    tbl = [(True, True, True), (True, False, False), (False, True, False), (False, False, False)]
    obs = [frog.success_gate(s, c) for s, c, _ in tbl]
    p.check("truth_table", "gate truth table", [e for _, _, e in tbl], obs, obs == [e for _, _, e in tbl])
    p.raises("non_bool", "integer flag rejected (no silent truthiness)", lambda: frog.success_gate(1, True), frog.ViolationError)
    rng = np.random.default_rng(seed); n = 500; S = rng.random(n) < .6; C = rng.random(n) < .8; ns = rng.integers(10, 900, n)
    r = [frog.shaped_reward(bool(s), bool(c), not bool(c), int(k), 200, 0.5) for s, c, k in zip(S, C, ns)]
    viol = sum(1 for s, c, k, v in zip(S, C, ns, r) if not (s and c) and v not in (0.0, 0.5))
    p.check("gate_enforced_in_reward", "trajectories failing the gate never receive a length-shaped value", 0, viol, viol == 0)
    p.interfaces = {"producer": "task verifier (success) + rollout engine (completed)", "consumer": "length adjustment"}; p.results = ["Gate truth table and enforcement inside shaped_reward verified on %d random trajectories." % n]
    return p

def _count_pair(pid, locpages, seed):
    p = Pair(pid, "Measurement", ["frog.py"])
    _spec(p, "Assistant(-generated) token count n.", "n = number of model-generated tokens (reasoning + natural language + tool calls); tool observations/prompt excluded", [LOC_42],
          {"inputs": "per-token role labels", "output": "int n"}, ["role taxonomy (reasoning,text,tool_call | prompt,observation) is the fixture's labelling"], {}, locpages)
    ex = ["prompt"] * 5 + ["reasoning"] * 7 + ["tool_call"] * 3 + ["observation"] * 11 + ["text"] * 4
    p.check("known_example", "hand-counted trajectory: 7+3+4", 14, frog.assistant_token_count(ex), frog.assistant_token_count(ex) == 14)
    p.check("empty", "empty trajectory counts 0", 0, frog.assistant_token_count([]), frog.assistant_token_count([]) == 0)
    rng = np.random.default_rng(seed); roles = list(rng.choice(frog.MODEL_ROLES + frog.MASKED_ROLES, 1000))
    p.check("recomputable", "matches collections-free recount", sum(1 for r in roles if r in ("reasoning", "text", "tool_call")), frog.assistant_token_count(roles), frog.assistant_token_count(roles) == sum(1 for r in roles if r in ("reasoning", "text", "tool_call")))
    p.raises("unknown_role", "unknown role rejected", lambda: frog.assistant_token_count(["reasoning", "sys"]), frog.ViolationError)
    p.rec("estimand", "count of model-generated tokens per trajectory (observation tokens excluded)")
    p.interfaces = {"producer": "tokenised trajectory with roles", "consumer": "length adjustment"}; p.results = ["Count estimand verified on known and random examples."]
    return p

def _logpen_pair(pid, wt, locpages):
    p = Pair(pid, wt, ["frog.py", "frog_sim.py"])
    _spec(p, "Logarithmic length adjustment/penalty.", "1 if n<=N else 1-alpha ln(n/N)", [LOC_42], {"inputs": "n, N>0, alpha>=0", "output": "float"},
          ["alpha,N not source-given (fixture N=200, alpha=0.5)", "not clipped"], {"N": 200, "alpha": 0.5}, locpages)
    N, al = 200, 0.5
    for n_, e in [(0, 1.0), (200, 1.0), (201, 1 - al * math.log(201 / 200)), (400, 1 - al * math.log(2)), (200 * math.e ** 2, 0.0)]:
        pass
    ns = [0, 200, 201, 400, int(round(200 * math.e ** 2))]
    obs = [frog.log_length_adjustment(n, N, al) for n in ns]; exp = [1.0 if n <= N else 1 - al * math.log(n / N) for n in ns]
    p.check("values", "values at 0, N, N+1, 2N, ~N e^2 (zero crossing)", exp, obs, np.allclose(exp, obs, atol=1e-15))
    mono = all(frog.log_length_adjustment(n + 1, N, al) <= frog.log_length_adjustment(n, N, al) for n in range(0, 3000))
    p.check("monotone_nonincreasing", "adjustment never increases with n", True, mono, mono)
    p.check("continuity_at_N", "left/right limits agree at n=N", 1.0, frog.log_length_adjustment(200.0000001, N, al), abs(frog.log_length_adjustment(200.0000001, N, al) - 1) < 1e-9)
    p.raises("negative_alpha", "alpha<0 rejected", lambda: frog.log_length_adjustment(10, N, -1), frog.ViolationError)
    if wt == "Workflow stage":
        out = frog.shaped_reward(True, True, False, 400, N, al)
        p.check("handoff_to_next_stage", "output feeds the group normaliser (C0015-02) without error", "finite advantage", out, math.isfinite(out) and frog.group_advantage(np.array([[out, 1.0, 0.0, 0.5]]))[1][0])
    else:
        a5 = frog_sim.length_policy_run(0.5); a0 = frog_sim.length_policy_run(0.0); p.rec("ablation", {"alpha_0.5": a5, "alpha_0": a0})
        p.check("contribution", "penalty shortens the fixture policy", "len(0.5)<len(0)", [a5["mean_len"], a0["mean_len"]], a5["mean_len"] < a0["mean_len"], kind="evaluation")
    p.interfaces = {"producer": "token count + gate", "consumer": "C0015-02 group normalisation"}; p.results = ["Log adjustment verified at boundary, zero-crossing, monotonicity and continuity."]
    return p

def C0081_01():
    p = _gate_pair("C0081-01", "2-3", 21); p.spec["purpose"] = "Task-success condition (verifier outcome) gating the efficiency reward."; return p
def C0081_02():
    p = _gate_pair("C0081-02", "2-3", 22); p.spec["purpose"] = "Completed-attempt condition (not truncated) gating the efficiency reward."
    p.check("truncated_correct_gets_half", "truncated-but-correct trajectory receives 0.5, not the length-shaped value", 0.5, frog.shaped_reward(True, False, True, 5000, 200, 0.5), frog.shaped_reward(True, False, True, 5000, 200, 0.5) == 0.5); return p
def C0081_03(): return _count_pair("C0081-03", "2-3", 23)
def C0081_04(): return _logpen_pair("C0081-04", "Workflow stage", "2-3")
def C0085_01(): return _count_pair("C0085-01", "3", 31)
def C0085_02(): return _gate_pair("C0085-02", "3", 32)
def C0085_03(): return _logpen_pair("C0085-03", "Loss", "3")
def C0086_01():
    p = _count_pair("C0086-01", "5", 41); p.open_issues.append("C0086 duplicates C0085 in the catalog; validated independently with different seeds."); return p
def C0086_02():
    p = _gate_pair("C0086-02", "5", 42); p.open_issues.append("C0086 duplicates C0085 in the catalog."); return p
def C0086_03():
    p = _logpen_pair("C0086-03", "Loss", "5"); p.open_issues.append("C0086 duplicates C0085 in the catalog."); return p

PAIRS = {f.__name__.replace("_", "-"): f for f in [C0015_01, C0015_02, C0015_03, C0064_01, C0064_02, C0064_03, C0064_04, C0079_01, C0079_02, C0079_03, C0079_04,
                                                   C0081_01, C0081_02, C0081_03, C0081_04, C0085_01, C0085_02, C0085_03, C0086_01, C0086_02, C0086_03]}
