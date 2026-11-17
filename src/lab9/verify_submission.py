"""Reproduce public submission checks and preserve their actual stdout/exit codes.
Run from src: python -m lab9.verify_submission
"""
import json
import os
from pathlib import Path
import subprocess
import sys

def main():
    steps=[
        (0,["lab9.smoke"]),
        (0,["lab9.evalset","--check"]),(0,["lab9.evalset","--v2","--check"]),
        (0,["pytest","-q","-m","student","-o","addopts=","-k","lab9"]),
        (0,["lab9.judge","--csv","data/eval/judge_tone_public.csv","--audit","5"]),
        (1,["lab9.judge","--csv","data/eval/judge_helpful_public.csv","--audit","5"]),
        (0,["lab9.gate","--pr","reports/baseline_v1.json","--baseline","reports/baseline_v1.json"]),
        (0,["lab9.ci_check","--pr","reports/baseline_v1.json","--baseline","reports/baseline_v1.json"]),
        (0,["lab9.gate","--pr","reports/eval_fixed.json","--baseline","reports/baseline_v1.json"]),
        (1,["lab9.gate","--pr","reports/eval_seeded_regression.json","--baseline","reports/baseline_v1.json"]),
        (0,["lab9.mutation","--detect"]),
        (0,["lab9.mutation","--spec","config/metric_spec_v2.yaml","--baseline","reports/baseline_v2.json"]),
        (0,["lab9.mutation","--spec","config/metric_spec_v2.yaml","--aa","66,77,88,99,110"]),
        (0,["lab9.eval","--shape","slice_regression","--spec","config/metric_spec_v2.yaml","--out","reports/eval_slice_regression.json"]),
        (0,["lab9.traps","--pr","reports/eval_slice_regression.json","--baseline","reports/baseline_v2.json","--spec","config/metric_spec_v2.yaml"]),
        (0,["lab9.gate","--pr","reports/baseline_v2.json","--baseline","reports/baseline_v2.json","--spec","config/metric_spec_v2.yaml"]),
    ]
    # Prove each trap's CLI returns a deliberate exit 1, including the ratchet.
    for trap in ("evaluator_errors_as_nan","dropped_failing_rows","cherry_picked_seeds","loosened_spec"):
        args=["lab9.gate","--pr",f"reports/traps/{trap}.json","--baseline","reports/baseline_v2.json","--spec","config/metric_spec_v2.yaml"]
        if trap=="loosened_spec":args[-1]="reports/traps/loosened_spec.spec.yaml";args += ["--base-spec","config/metric_spec_v2.yaml"]
        steps.append((1,args))
    out=[]
    for expected,args in steps:
        cmd=[sys.executable,"-m",*args]
        res=subprocess.run(cmd,text=True,encoding="utf-8",errors="replace",capture_output=True,
                           env={**os.environ,"PYTHONUTF8":"1"})
        ok=res.returncode==expected
        out.append(dict(command="python -m "+" ".join(args),expected=expected,exit_code=res.returncode,ok=ok,stdout=res.stdout,stderr=res.stderr))
        print(f"{'PASS' if ok else 'FAIL'} exit {res.returncode} (expected {expected}): python -m {' '.join(args)}",flush=True)
        if not ok:print(res.stdout,res.stderr,flush=True)
    Path("reports/verification.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    Path("reports/verification.txt").write_text("\n\n".join(f"$ {r['command']}\n{r['stdout']}\n{r['stderr']}exit={r['exit_code']} expected={r['expected']}" for r in out),encoding="utf-8")
    return 0 if all(r["ok"] for r in out) else 1

if __name__=="__main__": raise SystemExit(main())
