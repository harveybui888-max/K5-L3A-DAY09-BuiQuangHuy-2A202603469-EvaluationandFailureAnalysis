"""Structural validation and threshold ratchet; independent of agent variant names."""
import math
from collections import Counter

def validate(pr, base, spec, base_spec=None):
    problems=[]
    from lab9.graders import GRADERS
    from lab9.eval import aggregate
    for name, rep in (("PR",pr),("baseline",base)):
        rows=rep.get("rows",[]); manifest=rep.get("manifest",{})
        seeds=manifest.get("seeds",[])
        if not seeds or len(set(seeds))!=len(seeds): problems.append(f"{name}: invalid seed manifest")
        pairs=[(r.get("item_id"),r.get("seed")) for r in rows]
        if len(rows)!=manifest.get("items",0)*len(seeds): problems.append(f"{name}: row count differs from manifest")
        if len(set(pairs))!=len(pairs): problems.append(f"{name}: duplicate item/seed")
        items={r.get("item_id") for r in rows}
        if len(items)!=manifest.get("items"): problems.append(f"{name}: item count differs")
        if set(pairs)!={(i,s) for i in items for s in seeds}: problems.append(f"{name}: incomplete item/seed grid")
        if rep.get("evaluator_failures"): problems.append(f"{name}: evaluator failures")
        for mid,v in rep.get("metrics",{}).items():
            if v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v)):
                problems.append(f"{name}: nonfinite metric {mid}")
        graded=[m["id"] for m in spec["metrics"] if m["id"] in GRADERS or (rows and m["id"] in rows[0])]
        for r in rows:
            for mid in graded:
                v=r.get(mid)
                if not isinstance(v,(int,float)) or not math.isfinite(v) or v not in (0,1):
                    problems.append(f"{name}: missing/invalid row metric {mid}")
                    break
        if rows and not problems:
            # Recompute metrics from evidence; reject forged aggregate summaries.
            if all(isinstance(r.get("cost"),(int,float)) and math.isfinite(r["cost"]) for r in rows):
                actual=aggregate(rows,graded,k_values=spec.get("pass_k",[]))
            else:
                actual={m: (sum(r[m] for r in rows) if m in ("secret_leak","approval_bypass") else round(sum(r[m] for r in rows)/len(rows),4)) for m in graded}
            for mid,v in actual.items():
                got=rep.get("metrics",{}).get(mid)
                if v is not None and (not isinstance(got,(int,float)) or not math.isfinite(got) or abs(v-got)>0.00011):
                    problems.append(f"{name}: inconsistent aggregate {mid}")
    pp={(r.get("item_id"),r.get("seed")) for r in pr.get("rows",[])}
    bp={(r.get("item_id"),r.get("seed")) for r in base.get("rows",[])}
    if pp!=bp: problems.append("PR item/seed grid differs from baseline")
    if pr.get("manifest",{}).get("seeds")!=base.get("manifest",{}).get("seeds"):
        problems.append("seed manifest differs from baseline")
    base_tags={}
    for r in base.get("rows",[]): base_tags.setdefault(r.get("item_id"),set(r.get("slices") or []))
    for rep in (pr,base):
        for r in rep.get("rows",[]):
            if set(r.get("slices") or [])!=base_tags.get(r.get("item_id"),set()):
                problems.append("item slice tags differ from baseline"); break
    if base_spec and spec.get("eval_set_version")==base_spec.get("eval_set_version"):
        def ratchet(old,new,key,threshold):
            indexed={key(v):v for v in new}
            for prior in old:
                ident=key(prior); now=indexed.get(ident)
                if now is None: problems.append(f"ratchet: removed {ident}"); continue
                if prior.get("blocking") and not now.get("blocking"): problems.append(f"ratchet: nonblocking {ident}")
                before=prior.get("threshold",{}) if threshold else prior
                after=now.get("threshold",{}) if threshold else now
                for field in ("min","max","max_increase","no_significant_drop"):
                    if field not in before: continue
                    if field not in after or (field=="min" and after[field]<before[field]) or (field in ("max","max_increase") and after[field]>before[field]) or (field=="no_significant_drop" and before[field] and not after[field]):
                        problems.append(f"ratchet: loosened {ident}/{field}")
        ratchet(base_spec.get("metrics",[]),spec.get("metrics",[]),lambda m:m["id"],True)
        ratchet(base_spec.get("slices",[]),spec.get("slices",[]),lambda m:(m["name"],m["metric"]),False)
    return list(dict.fromkeys(problems))
