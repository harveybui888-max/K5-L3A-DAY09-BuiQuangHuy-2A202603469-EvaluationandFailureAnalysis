"""Offline calibration and paired statistical estimators."""
from collections.abc import Sequence
from math import comb, isfinite
import numpy as np
from scipy.stats import bootstrap
POS = "FAIL"

def confusion(human, judge):
    if len(human) != len(judge) or not human:
        raise ValueError("nonempty paired labels required")
    out = dict(tp=0, fp=0, fn=0, tn=0)
    for h,j in zip(human,judge):
        if h not in ("PASS","FAIL") or j not in ("PASS","FAIL"):
            raise ValueError("labels must be PASS or FAIL")
        out[("tp" if h==POS else "fp") if j==POS else ("fn" if h==POS else "tn")] += 1
    return out

def precision_recall(human, judge):
    d=confusion(human,judge)
    return (d['tp']/(d['tp']+d['fp']) if d['tp']+d['fp'] else 0.,
            d['tp']/(d['tp']+d['fn']) if d['tp']+d['fn'] else 0.)

def cohen_kappa(human, judge):
    d=confusion(human,judge); n=sum(d.values())
    po=(d['tp']+d['tn'])/n
    pe=((d['tp']+d['fn'])*(d['tp']+d['fp'])+(d['tn']+d['fp'])*(d['tn']+d['fn']))/n**2
    if pe==1: raise ValueError("undefined kappa")
    return (po-pe)/(1-pe)

def rogan_gladen(observed_rate, sensitivity, specificity):
    if any(not isfinite(v) or not 0<=v<=1 for v in (observed_rate,sensitivity,specificity)):
        raise ValueError("rates must be finite probabilities")
    den=sensitivity+specificity-1
    if den<=0: raise ValueError("judge must outperform chance")
    return min(1.,max(0.,(observed_rate+specificity-1)/den))

def paired_bootstrap(a,b,*,n_resamples=1000,rng=2027,confidence=.95):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape or not len(a) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("finite paired vectors required")
    if n_resamples<1 or not 0<confidence<1: raise ValueError("invalid bootstrap settings")
    delta=float(np.mean(a)-np.mean(b))
    if np.array_equal(a,b): return 0.,0.,0.
    if len(a)==1: return delta,delta,delta
    ci=bootstrap((a,b),lambda x,y,axis: np.mean(x,axis=axis)-np.mean(y,axis=axis),paired=True,
                 method="percentile",n_resamples=n_resamples,rng=np.random.default_rng(rng),confidence_level=confidence).confidence_interval
    return delta,float(ci.low),float(ci.high)

def _validate(n,c,k):
    if any(type(v) is not int for v in (n,c,k)) or n<1 or not 0<=c<=n or not 1<=k<=n:
        raise ValueError("require integer n>=1, 0<=c<=n, 1<=k<=n")

def pass_at_k(n,c,k):
    _validate(n,c,k)
    return 1-comb(n-c,k)/comb(n,k)

def pass_hat_k(n,c,k):
    _validate(n,c,k)
    return comb(c,k)/comb(n,k)
