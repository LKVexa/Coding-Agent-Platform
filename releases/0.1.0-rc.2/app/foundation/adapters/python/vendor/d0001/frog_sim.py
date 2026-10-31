"""Toy fixtures (labeled study fixtures, NOT the source's coding-agent training) used to evaluate the contribution
of the FrogNano objective terms. All seeds explicit."""
import numpy as np
from . import frog

LEN_BINS = np.array([50, 100, 200, 400, 800, 1600])
P_SUCCESS = np.array([0.20, 0.50, 0.70, 0.75, 0.78, 0.80])
MAX_CTX = 1000   # bins above are truncated (incomplete)

def length_policy_run(alpha, N=200, steps=300, G=8, tasks=4, lr=0.5, seed=0, use_shaping=True):
    rng = np.random.default_rng(seed); th = np.zeros(len(LEN_BINS)); dropped = 0
    for _ in range(steps):
        pi = frog.softmax(th); a = rng.choice(len(LEN_BINS), size=(tasks, G), p=pi)
        succ = rng.random((tasks, G)) < P_SUCCESS[a]; trunc = LEN_BINS[a] > MAX_CTX
        R = np.zeros((tasks, G))
        for i in range(tasks):
            for j in range(G):
                n = int(LEN_BINS[a[i, j]])
                R[i, j] = frog.shaped_reward(bool(succ[i, j]), not trunc[i, j], bool(trunc[i, j]), n, N, alpha) if use_shaping \
                    else (1.0 if (succ[i, j] and not trunc[i, j]) else (0.5 if (succ[i, j] and trunc[i, j]) else 0.0))
        A, keep = frog.group_advantage(R); dropped += int((~keep).sum())
        g = np.zeros_like(th)
        for i in range(tasks):
            for j in range(G):
                oh = np.eye(len(th))[a[i, j]]; g += A[i, j] * (oh - pi)
        th += lr * g / (tasks * G)
    pi = frog.softmax(th)
    return {"pi": pi.round(4).tolist(), "mean_len": float(pi @ LEN_BINS),
            "success_rate": float(pi @ (P_SUCCESS * (LEN_BINS <= MAX_CTX))), "dropped_groups": dropped}

def token_policy_run(use_mask, steps=150, B=16, L=16, V=10, lr=4.0, stale=4, seed=0, target=3):
    """Off-policy (stale-behaviour) token-level REINFORCE with ratio rho=p/q and optional divergence mask."""
    rng = np.random.default_rng(seed); th = np.zeros(V); hist = [th.copy()]; kept_frac = []; maxdp = []
    for _ in range(steps):
        thq = hist[max(0, len(hist) - 1 - stale)]; q = frog.softmax(thq); p = frog.softmax(th)
        toks = rng.choice(V, size=(B, L), p=q); R = (toks == target).mean(axis=1, keepdims=True)
        R = R.reshape(2, B // 2)                       # 2 tasks x 8 trajectories
        A, keep = frog.group_advantage(R); A = A.reshape(B, 1) * np.ones((1, L))
        pt = p[toks]; qt = q[toks]; tr = np.ones_like(pt, bool)
        if use_mask:
            k, _ = frog.token_selection(A, pt, qt, tr)
        else:
            k = tr
        rho = pt / qt; g = np.zeros(V)
        for b in range(B):
            for t in range(L):
                if k[b, t]:
                    oh = np.zeros(V); oh[toks[b, t]] = 1
                    g += A[b, t] * rho[b, t] * (oh - p)      # d(A rho)/dth
        th = th + lr * g / tr.sum(); hist.append(th.copy())
        kept_frac.append(float(k.mean())); maxdp.append(float(np.abs(pt - qt).max()))
    p = frog.softmax(th)
    return {"final_p_target": float(p[target]), "mean_kept_fraction": float(np.mean(kept_frac)),
            "max_abs_dp": float(np.max(maxdp)), "final_entropy": float(-(p * np.log(p + 1e-300)).sum())}

def consolidation_run(mode, V=256, steps=300, lr=0.5, seed=0, n_ctx=32):
    """Student logits per context trained toward a fixed reference; targets agree with reference top-1 in 75% of
    contexts. mode: 'topk' (source rule) or 'ce_only' (comparator: cross-entropy on target everywhere)."""
    rng = np.random.default_rng(seed); ref = rng.normal(0, 3, (n_ctx, V)); S = np.zeros((n_ctx, V))
    tgt = np.array([int(np.argmax(r)) if rng.random() < 0.75 else int(rng.integers(V)) for r in ref])
    for _ in range(steps):
        for c in range(n_ctx):
            g = frog.consolidation_grad(S[c], ref[c], tgt[c]) if mode == "topk" else (frog.softmax(S[c]) - np.eye(V)[tgt[c]])
            S[c] -= lr * g
    agree = [c for c in range(n_ctx) if frog.agreement(tgt[c], ref[c])]
    kl = [float(np.sum(frog.softmax(ref[c]) * (frog.log_softmax(ref[c]) - frog.log_softmax(S[c])))) for c in agree]
    top1 = float(np.mean([np.argmax(S[c]) == np.argmax(ref[c]) for c in agree]))
    tgt_hit = float(np.mean([np.argmax(S[c]) == tgt[c] for c in range(n_ctx)]))
    return {"agree_contexts": len(agree), "mean_full_vocab_kl_on_agree": float(np.mean(kl)),
            "top1_match_on_agree": top1, "target_top1_rate_all": tgt_hit}
