"""FrogNano RL-objective pipeline (uploaded article = arXiv 2609.07925v2, Sec. RL objective, p.3).
Source-stated: group-relative advantage A=(R-mean)/(std+1e-6) over the G trajectories of one task; zero-variance
groups dropped (on raw task rewards); advantage broadcast to model-generated tokens; tool observations and prompt
masked; rho=p/q, dp=p-q; token dropped if (A>0 and dp>0.2) or (A<=0 and dp<-0.2); L=-(1/|T|) sum_{t in K} A_t rho_t
with T = all trainable tokens; no reference-KL, no entropy bonus. Length shaping: R=1 if n<=N else 1-alpha*ln(n/N)
for completed successful trajectories; truncated-but-correct 0.5; failure 0. Consolidation: KL on top-64 logits when
the target token equals the reference top-1, otherwise cross-entropy.
Not source-given (explicit arguments / labeled assumptions): alpha, N, std ddof (0), KL direction (ref||student),
top-64 renormalisation, whether the shaped reward may be negative (not clipped)."""
import numpy as np

EPS = 1e-6
THRESH = 0.2
TOPK = 64
MODEL_ROLES = ("reasoning", "text", "tool_call")   # model-generated, counted and trainable
MASKED_ROLES = ("prompt", "observation")           # never trainable, never counted

class ViolationError(ValueError):
    """Raised (never silently converted to success) when an input violates a declared contract."""

# ---------- C0015-02 within-task reward normalisation ----------
def group_advantage(R, eps=EPS, ddof=0):
    """R: (n_groups, G) raw task rewards. Returns (A, keep) with A=(R-mean)/(std+eps); keep[g]=False for
    zero-variance groups (their A rows are set to 0 and they must be dropped by the consumer)."""
    R = np.asarray(R, dtype=float)
    if R.ndim != 2 or R.shape[1] < 2:
        raise ViolationError("rewards must be (n_groups, G>=2)")
    if not np.all(np.isfinite(R)):
        raise ViolationError("non-finite reward")
    mu = R.mean(axis=1, keepdims=True); sd = R.std(axis=1, ddof=ddof, keepdims=True)
    keep = (sd[:, 0] > 0)
    A = (R - mu) / (sd + eps)
    A[~keep] = 0.0
    return A, keep

# ---------- C0081/C0085/C0086 length accounting & shaping ----------
def assistant_token_count(roles):
    """n = number of model-generated tokens (reasoning + natural language + tool-call); observations/prompt excluded."""
    bad = [r for r in roles if r not in MODEL_ROLES + MASKED_ROLES]
    if bad:
        raise ViolationError("unknown token role(s): %s" % sorted(set(bad)))
    return int(sum(r in MODEL_ROLES for r in roles))

def success_gate(success, completed):
    """Penalty applies only to completed successful trajectories."""
    if not isinstance(success, (bool, np.bool_)) or not isinstance(completed, (bool, np.bool_)):
        raise ViolationError("success/completed must be booleans")
    return bool(success) and bool(completed)

def log_length_adjustment(n, N, alpha):
    """1 if n<=N else 1-alpha*ln(n/N) (non-strict at n==N). Not clipped (source gives no clip)."""
    if N <= 0 or alpha < 0 or n < 0:
        raise ViolationError("require N>0, alpha>=0, n>=0")
    return 1.0 if n <= N else 1.0 - alpha * np.log(n / N)

def shaped_reward(success, completed, truncated, n, N, alpha):
    if truncated and completed:
        raise ViolationError("a trajectory cannot be both truncated and completed")
    if success_gate(success, completed):
        return log_length_adjustment(n, N, alpha)
    if truncated and success:
        return 0.5
    return 0.0

# ---------- C0015-01 / C0064 token selection ----------
def token_selection(A_tok, p, q, trainable, thresh=THRESH):
    """Returns (keep, reason) arrays. keep = trainable & not dropped. Strict inequalities as in the source
    ('exceeds'): dp == +-0.2 is retained."""
    A_tok, p, q, trainable = map(np.asarray, (A_tok, p, q, trainable))
    if not (A_tok.shape == p.shape == q.shape == trainable.shape):
        raise ViolationError("shape mismatch")
    if np.any((p < 0) | (p > 1) | (q <= 0) | (q > 1)):
        raise ViolationError("probabilities must satisfy 0<=p<=1, 0<q<=1")
    dp = p - q
    drop = trainable.astype(bool) & (((A_tok > 0) & (dp > thresh)) | ((A_tok <= 0) & (dp < -thresh)))
    keep = trainable.astype(bool) & ~drop
    reason = np.where(~trainable.astype(bool), "masked_role", np.where(drop, np.where(A_tok > 0, "dp_gt_+thr", "dp_lt_-thr"), "kept"))
    return keep, reason

def policy_loss(A_tok, p, q, trainable, thresh=THRESH):
    """L = -(1/|T|) sum_{t in K} A_t rho_t. |T| = number of trainable tokens (denominator NOT reduced by exclusion).
    Returns dict with loss, per-token contributions, K mask, |T|; |T|==0 -> explicit zero-signal state."""
    keep, reason = token_selection(A_tok, p, q, trainable, thresh)
    T = int(np.asarray(trainable).astype(bool).sum())
    rho = np.asarray(p, float) / np.asarray(q, float)
    contrib = np.where(keep, -np.asarray(A_tok, float) * rho, 0.0)
    if T == 0:
        return {"loss": 0.0, "T": 0, "K": 0, "state": "zero_signal_no_trainable_tokens", "keep": keep, "contrib": contrib, "reason": reason}
    st = "ok" if keep.any() else "zero_signal_all_excluded"
    return {"loss": float(contrib.sum() / T), "T": T, "K": int(keep.sum()), "state": st, "keep": keep, "contrib": contrib, "reason": reason}

def broadcast_advantage(A_traj, roles):
    """Broadcast a trajectory advantage to its tokens; trainable = model-generated roles."""
    assistant_token_count(roles)
    tr = np.array([r in MODEL_ROLES for r in roles])
    return np.where(tr, A_traj, 0.0), tr

# ---------- C0079 top-64 consolidation ----------
def softmax(z):
    z = np.asarray(z, float); m = z.max(axis=-1, keepdims=True); e = np.exp(z - m); return e / e.sum(axis=-1, keepdims=True)

def log_softmax(z):
    z = np.asarray(z, float); m = z.max(axis=-1, keepdims=True); return z - m - np.log(np.exp(z - m).sum(axis=-1, keepdims=True))

def reference_topk(ref_logits, k=TOPK):
    """Indices of the reference model's k largest logits (ties broken by lower index, deterministic)."""
    ref_logits = np.asarray(ref_logits, float)
    if ref_logits.ndim != 1 or not np.all(np.isfinite(ref_logits)):
        raise ViolationError("reference logits must be a finite 1-D vector")
    if k < 1 or k > ref_logits.shape[0]:
        raise ViolationError("top-k=%d incompatible with vocabulary %d" % (k, ref_logits.shape[0]))
    order = np.lexsort((np.arange(ref_logits.size), -ref_logits))
    return order[:k]

def agreement(target_id, ref_logits):
    return int(target_id) == int(reference_topk(ref_logits, 1)[0])

def consolidation_loss(student_logits, ref_logits, target_id, k=TOPK):
    """If target == reference top-1: KL(p_ref^k || p_student^k) over the reference top-k indices, both renormalised
    over those k (assumption). Else: cross-entropy -log softmax(student)[target] over the full vocabulary."""
    s = np.asarray(student_logits, float)
    if s.shape != np.asarray(ref_logits).shape:
        raise ViolationError("student/reference vocab mismatch")
    if not (0 <= int(target_id) < s.size):
        raise ViolationError("target id out of range")
    idx = reference_topk(ref_logits, k)
    if agreement(target_id, ref_logits):
        lp = log_softmax(np.asarray(ref_logits, float)[idx]); lq = log_softmax(s[idx])
        return {"branch": "topk_kl", "loss": float(np.sum(np.exp(lp) * (lp - lq))), "idx": idx}
    return {"branch": "cross_entropy", "loss": float(-log_softmax(s)[int(target_id)]), "idx": idx}

def consolidation_grad(student_logits, ref_logits, target_id, k=TOPK):
    """Analytic gradient w.r.t. student logits."""
    s = np.asarray(student_logits, float); g = np.zeros_like(s)
    out = consolidation_loss(s, ref_logits, target_id, k); idx = out["idx"]
    if out["branch"] == "topk_kl":
        g[idx] = softmax(s[idx]) - softmax(np.asarray(ref_logits, float)[idx])
    else:
        g = softmax(s); g[int(target_id)] -= 1.0
    return g
