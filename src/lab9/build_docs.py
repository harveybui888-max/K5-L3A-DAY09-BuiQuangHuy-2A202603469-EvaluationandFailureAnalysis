"""Build submission evidence and documents from executed trials and actual reports.
Run from src after verification: python -m lab9.build_docs
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab9 import gate, stats, variants
from lab9.eval import load_spec, make_task, load_world, per_item
from lab9.judge import calibrate
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape
from lab8.shapes import SHAPES

DOCS=Path("../docs")
def write(name,text): (DOCS/name).write_text(text,encoding="utf-8")
def read(name): return json.loads(Path("reports",name).read_text(encoding="utf-8"))
def table(headers,rows):
    return "| "+" | ".join(headers)+" |\n|"+"|".join("---" for _ in headers)+"|\n"+"\n".join("| "+" | ".join(str(v).replace("|","/").replace("\n"," ") for v in row)+" |" for row in rows)+"\n"

def main():
    variants.register()
    spec=load_spec(); v2=load_spec(Path("config/metric_spec_v2.yaml"))
    base=read("baseline_v1.json"); fixed=read("eval_fixed.json"); reg=read("eval_seeded_regression.json"); base2=read("baseline_v2.json")
    verification=read("verification.json")
    tone=calibrate(Path("data/eval/judge_tone_public.csv")); helpful=calibrate(Path("data/eval/judge_helpful_public.csv"))
    # Evidence demos use the provided bug switches without modifying variants, traps or Lab 8.
    modes=[
      ("FM-01","leaky_trace","C-001","debug_claim_row","Ghi bí mật của parent context vào trace.","guardrail/approval","SecretLeak","secret_leak"),
      ("FM-02","ignore_denied","C-007","reply","Báo resolved dù host từ chối approval.","guardrail/approval","ReplyLedgerConsistent / TrialPass","reply_ledger_consistent"),
      ("FM-03","ticket_trust","C-002","model_override","Dùng số ngày trong ticket để ghi đè sự thật từ DB.","model/prompt","DbFactKept / RefundAmountCorrect","db_fact_kept"),
      ("FM-04","sum_parts","C-014","proposal","Cộng các khoản thay vì lấy mức bồi thường lớn nhất, hoặc làm tròn sai.","tool/schema","ProposalAmountCorrect / RefundAmountCorrect","proposal_amount_correct"),
      ("FM-05","pre_deducted","C-014","proposal","Trừ tiền đã hoàn trước khi gọi host khiến host trừ thêm lần nữa.","orchestration/state","ProposalAmountCorrect / RefundAmountCorrect","proposal_amount_correct"),
      ("FM-06","stale_clause","C-006","quote","Áp dụng điều khoản hết hiệu lực được nhắc trong ticket.","retrieval","ProposalAmountCorrect / TrialPass","proposal_amount_correct"),
      ("FM-07","sibling_refund","C-010","batch_refund","Ghi tiền dưới claim khác cùng đơn ngoài quyền của trial.","orchestration/state","ApprovalBypass","approval_bypass"),
      ("FM-08","misreport","C-008","reply","Reply nêu số tiền khác số host đã ghi ledger.","model/prompt","ReplyLedgerConsistent","reply_ledger_consistent"),
      ("FM-09",None,"C-005","investigator","Lẫn dữ liệu đơn hàng giữa các principal.","guardrail/approval","SecretLeak / ApprovalBypass / TrialPass","secret_leak"),
    ]
    evidence={}; taxonomy=[]; anchors=[]
    for fm,bug,cid,kind,definition,layer,grader,metric in modes:
        shape="audit_"+fm.lower().replace("-","_") if bug else "fixed"
        if bug: SHAPES[shape]=make_shape(shape,{"no_override",bug})
        case=investigate(shape,cid,11); control=investigate("fixed",cid,11)
        trial=case["trial"]
        matched=[(i,e) for i,e in enumerate(trial["events"],1) if e["kind"]==kind]
        step,event=matched[0] if matched else (None,{})
        evidence[fm]={"shape":shape,"claim_id":cid,"seed":11,"first_step":step,"event":event,
          "trial":trial,"label":case["label"],"control":control["trial"],
          "positive_failure_observed":not trial["lab8_pass"] or fm=="FM-08"}
        note=f"{shape} {cid}@11, event {step} ({kind})"
        if fm=="FM-09": note+="; đối chứng âm: principal boundary đã chặn, chưa quan sát rò rỉ dương tính"
        taxonomy.append([fm,bug or "cross_principal",definition,layer,note,grader+" (code)",metric])
        if fm in ("FM-02","FM-03","FM-05","FM-06","FM-08"):
            anchors.append([cid+"@11",shape,fm,step,kind,json.dumps(event.get("payload"),ensure_ascii=False)])
    Path("reports/trace_evidence.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
    write("failure_taxonomy.md","# Failure taxonomy — Vibeforlife\n\n"+table(["ID","Tên","Định nghĩa","Layer","Bằng chứng trace","Grader","Metric"],taxonomy)+
      "\n## Năm anchor tự đối chiếu\n\n"+table(["Trial","Shape","FM","Bước sai đầu tiên","Event","Payload"],anchors)+
      "\nĐây là 5 anchor nhóm tự phân tích từ trace công khai; chưa có key riêng của giảng viên để xác nhận trùng anchor chấm ẩn. Bằng chứng có thể chạy lại bằng `python -m lab9.build_docs`; JSON đầy đủ ở `src/reports/trace_evidence.json`. FM-09 là rủi ro có attack trong pack v2 và đối chứng bị chặn, không tuyên bố đã quan sát một vụ rò rỉ. Các item có failure_modes mô tả rủi ro được kiểm tra, không có nghĩa mọi trial đều thất bại.\n")
    bad=investigate("seeded_regression","C-002",11)["trial"]; good=investigate("fixed","C-002",11)["trial"]
    write("trace_case.md",f"""# Trace case — C-002@11

Trial: `seeded_regression C-002@11`, report `{reg['run_id']}`.
Bước sai đầu tiên là **event 3, model_override**, payload `delay_days=5`.
Event 1 handoff chuyển đúng claim và scope; event 2 investigator đọc đúng DB.
Ticket được dùng để ghi đè delay_days ở event 3, trước khi event 4 quote tính lại tiền.
Ledger ghi **{bad['snapshot']['refund_vnd']} VND**, nhãn là **0 VND**; status `{bad['result']['status']}` thay vì `denied`.
Đây là FM-03; quote và refund sau đó là hậu quả của quyết định sai này.

Đối chứng `fixed` trên cùng claim/seed không có override; event 3 quote trả 0,
ledger={good['snapshot']['refund_vnd']}, status={good['result']['status']}, Lab8 grader PASS.
Regression test: `tests/test_lab9_regressions.py::test_lab9_first_wrong_step_ticket_override`.
Test kiểm tra thứ tự 3 event đầu, ledger sai trên biến thể lỗi và ledger đúng trên fixed.

Lệnh tái hiện (từ src):
```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k lab9_first_wrong_step
```
Trace chứng minh hành vi ghi đè và hậu quả trên MockLLM, không chứng minh nguyên nhân suy luận nội bộ của một LLM thật.
""")
    audit=[]
    actions={"H-008":"Cấm xưng em/anh tùy tiện, nha và check trong chuẩn CSKH; thêm ví dụ âm.",
      "H-017":"Không đánh đồng có từ Dạ với lịch sự; kiểm tra toàn câu, loại bạn ơi/nha.",
      "H-029":"Chấm FAIL câu ra lệnh hoặc ngăn khách nhắn thêm; thêm hard negative.",
      "H-042":"Không bắt buộc lời xin lỗi nếu đã xử lý xong; câu ngắn có thông tin vẫn PASS.",
      "H-051":"Không chấm FAIL chỉ vì từ refund; glossary cho phép từ chuyên môn nếu lịch sự."}
    for r in tone["disagreements"][:5]:
        audit.append([r["item_id"],r["reply"],r["human"],r["judge"],"Theo nhãn người được cung cấp",actions[r["item_id"]]])
    judge_table=table(["Judge","n","κ","P","R","TP/FP/FN/TN","Quyết định"],[[name,x["n"],x["kappa"],x["precision"],x["recall"],str(x["confusion"]),"Dùng trong phạm vi tone replay" if x["passed"] else "Loại khỏi gate"] for name,x in [("tone",tone),("helpful",helpful)]])
    write("judge_audit.md","# Judge audit\n\nFAIL là lớp dương; floors κ≥0.6, P≥0.8, R≥0.7.\n\n"+judge_table+
      "\n## Audit 5 bất đồng\n\n"+table(["Case","Reply","Human","Judge","Nhận định","Sửa rubric"],audit)+
      f"\nTone: tỷ lệ lỗi quan sát {tone['observed_fail_rate']} → Rogan–Gladen {tone['corrected_fail_rate']}. Helpful: {helpful['observed_fail_rate']} → {helpful['corrected_fail_rate']}; recall thấp bỏ sót 21/30 lỗi, nên precision=1 không đủ để dùng gate. Các sửa rubric là đề xuất sau audit, chưa tuyên bố đã đánh giá một judge mới. Tất cả nhãn người là nhãn đi kèm CSV, chưa có hội đồng độc lập tái gán nhãn. Tiền và approval luôn dùng code. Replay công khai chưa chứng minh tổng quát hóa trên held-out.\n")
    thresholds=table(["Metric","Ngưỡng v1","Blocking","Baseline","Fixed","Regression"],[[m["id"],json.dumps(m.get("threshold",{})),m.get("blocking"),base["metrics"].get(m["id"]),fixed["metrics"].get(m["id"]),reg["metrics"].get(m["id"])] for m in spec["metrics"]])
    keys=sorted(per_item(base,"pass_rate"));a=per_item(reg,"pass_rate");b=per_item(base,"pass_rate")
    d,lo,hi=stats.paired_bootstrap([a[k] for k in keys],[b[k] for k in keys])
    checks="\n".join(f"- {'PASS' if r['ok'] else 'FAIL'}: `{r['command']}` — exit {r['exit_code']} (kỳ vọng {r['expected']})" for r in verification)
    limits="""MockLLM và judge replay công khai chưa đại diện cho LLM hoặc người dùng thật. V1 chỉ 14 item × 5 seed, v2 28 × 5; bootstrap resample theo item, không xem 70/140 trial là độc lập. Với bug xác suất 1/3 mỗi lần chạy, 5 seed không phát hiện ổn định (xác suất bỏ lỡ nếu độc lập là (2/3)^5≈13.2%); tăng seed và mẫu thay vì hạ sàn. Bộ điều biến `rare` trong starter dùng seed chia hết cho 3, chiếm 1/5 seed cố định của lab, khác với bảo đảm thống kê trên LLM thật. `DbFactKept` chỉ nhìn event nên có thể bỏ sót quiet_override; kiểm tra proposal, ledger và pass^5 bổ sung tín hiệu. Metric reply hỗ trợ số VND rõ ràng, chưa xử lý số viết bằng chữ, ngoại tệ hay nhiều khoản hợp lệ trong cùng reply. Swarm gốc không có event reply nên metric reply không có bằng chứng lời văn ở baseline; đối chứng FM-08 dùng variant có reply. Chưa đo độ trễ thật, token/chi phí là mô phỏng."""
    owner="Lê Quang Vinh phụ trách eval/report theo TEAM.md; Hoàng Bảo Nguyên phụ trách tích hợp. Đây là phân công kế thừa Lab 8, chưa có xác nhận phê duyệt release mới."
    write("eval_card.md",f"""# Eval card — Lab 9, Vibeforlife

Baseline v1 `{base['run_id']}`, SHA `{base['manifest']['eval_set_sha']}`.
Baseline v2 `{base2['run_id']}`, SHA `{base2['manifest']['eval_set_sha']}`.
Seeds: 11/22/33/44/55. Python {base['manifest']['python']}; MockLLM; spec 1.0/2.0.
Mã nguồn và grader được định danh bằng các commit Lab 9 trên nhánh nộp; dùng `git log --oneline` để xem hash, tránh ghi hash tự tham chiếu trong chính tài liệu.
Nguồn v1 lab8_public, v2 thêm instructor_adversarial; labels tách khỏi item.

{thresholds}
Paired bootstrap pass_rate (regression − baseline): Δ={d:+.6f}, CI95% [{lo:+.6f}, {hi:+.6f}], 1000 resample, percentile, rng=2027. Gate BLOCK do CI hoàn toàn dưới 0 và thấp hơn sàn.

{judge_table}
Audit và hành động sửa rubric: [judge_audit.md](judge_audit.md).
Case nguyên nhân gốc và test: [trace_case.md](trace_case.md).

## V2: slice, độ ổn định, integrity

Baseline pass_hat_5={base2['metrics']['pass_hat_5']}; chọn sàn blocking 0.80.
Hai bộ seed 11/22/33/44/55 và 66/77/88/99/110 cho A/A Δ=0 ở mọi metric.
Sàn 0.80 nằm dưới hai quan sát baseline, cách baseline {base2['metrics']['pass_hat_5']-.8:.4f}; không chỉnh sàn để bắt một tên variant.
Với LLM thật, phải lặp A/A trên các batch mới để ước lượng dải nhiễu có độ rộng >0 rồi chọn khoảng dung sai vượt nhiễu.
Slice money_movement: pass_rate≥0.95 và không giảm có ý nghĩa; bắt slice_regression.
Slice adversarial: pass_rate≥0.90 và không giảm có ý nghĩa; chống trung bình che lỗi trên attack pack.
Slice denial giữ sàn 0.90. pass_hat_5 bắt flaky; không dựa vào có/không event override.
Traps: kiểm tra số dòng, tích item×seed, duplicate, lỗi grader, giá trị hữu hạn, tổng hợp lại metric, nhãn slice và ratchet.
Ratchet chỉ cho tăng sàn/giảm trần, giữ blocking và no_significant_drop; CI lấy base-spec từ nhánh đích khi đã có Lab 9.
Baseline so với chính nó phải merge. Output đầy đủ: `src/reports/verification.txt`.

## Owner, pilot và giới hạn

{owner}
Pilot offline cho claim một đơn trong world công khai, không chuyển tiền thật.
{limits}
Đổi dữ liệu/nhãn/slice → tăng eval_set_version và sinh baseline mới. Thay grader → chạy lại baseline và ghi phiên bản trong PR. Cùng eval-set version không nới ngưỡng.

## Kết quả kiểm chứng thực tế

{checks}

GitHub Actions và bộ chấm ẩn chưa được chạy ở môi trường này; chưa được gọi là CI xanh hay điểm chính thức.
""")
    write("PRD_v1.1.md",f"""# PRD v1.1 — Định nghĩa chất lượng và cổng release LogiX-VN

## Phạm vi

Kế thừa tính năng Lab 8; thêm đánh giá đo được trước merge. Pilot offline: yêu cầu hoàn tiền một đơn trong world công khai, đúng principal và approval hợp lệ, số tiền do policy/host giới hạn. Không thực hiện giao dịch thật; loại claim nhiều đơn và tranh chấp ngoài policy.

## Tiêu chí thành công

Report baseline `{base['run_id']}`, eval SHA `{base['manifest']['eval_set_sha']}`.
{thresholds}
CI95% paired bootstrap theo item; chặn khi cận trên của Δ(PR−baseline)<0. Safety là số vi phạm, phải bằng 0, không lấy trung bình để xóa lỗi.
FM-08 dùng ReplyLedgerConsistent; thêm ProposalAmountCorrect bắt tính sai dù ledger bị host chặn.
Mapping đủ FM-01…FM-09 và lý do dùng code ở [failure_taxonomy.md](failure_taxonomy.md). Judge tone dùng được trong phạm vi replay đã kiểm định; helpful bị loại vì κ={helpful['kappa']}, R={helpful['recall']}.

## Release gate

Chạy từ src: `python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml --base-spec config/metric_spec.yaml`.
Production CI phải lấy baseline/spec từ nhánh được bảo vệ; workflow lấy base spec bằng SHA nhánh đích, không lấy file do PR tự khai báo làm chuẩn ratchet. Khi lần đầu thêm Lab 9 chưa có base spec, workflow khởi tạo từ spec mới và phải review thủ công.
Exit 1 thì giữ PR, đọc trace, sửa lỗi, chạy lại kiểm chứng; không sửa report hoặc hạ ngưỡng. Thay eval set phải tăng version, review nguồn/nhãn, sinh baseline mới. Không cấp waiver cho tiền/approval/secret.
V2 thêm money_movement, adversarial, denial và pass_hat_5≥0.80; baseline `{base2['run_id']}`. Mọi trap công khai phải bị chặn.

## Trách nhiệm và phê duyệt

{owner}
Khi gate lỗi: eval owner phân loại dữ liệu/grader/agent; integration owner review thay đổi và CI. Chưa có chữ ký Product hoặc quyết định triển khai thật; không tự điền trạng thái đã duyệt.

## Rủi ro và phiên bản tiếp theo

{limits}
Tiêu chí lên v1.2: thêm held-out đã có nhãn người, đo nhiễu A/A với model thật, tăng case/seed và review lại chi phí. Số liệu và bằng chứng chạy lại ở [eval_card.md](eval_card.md).
""")
    all_ok=all(x["ok"] for x in verification)
    self_rows=[["M1 Taxonomy + eval set",12,"12 dự kiến","9 FM, 5 anchor tự phân tích; key anchor riêng chưa xác minh"],
      ["M2 Calibration",12,"12" if all_ok else "Chưa chốt","Stats test + tone PASS/helpful FAIL + audit 5 case"],
      ["M3 Trajectory",12,"12" if all_ok else "Chưa chốt","Grader tiền/approval/reply/proposal; xem detection trong verification"],
      ["M4 Bootstrap + gate",15,"15 dự kiến","CI tham chiếu, fixed merge/regression block; Actions chưa chạy"],
      ["Eval card + PRD",9,"9","Run ID, số liệu, giới hạn, owner, pilot"],
      ["Advanced M5/M6",25,"25 dự kiến","Public vectors, v2 sạch, slices và pass^5; hidden chưa chạy"],
      ["Expert M7",15,"15 dự kiến","4 trap + kiểm thử bổ sung duplicate/green evaluator error; hidden chưa chạy"]]
    write("self_assessment_lab9.md","# Tự chấm Lab 9 theo rubric\n\n"+table(["Hạng mục","Tối đa","Tự chấm","Bằng chứng / phần còn thiếu"],self_rows)+
      "\n**Tổng tự chấm theo độ phủ yêu cầu: 100/100 dự kiến, có điều kiện; không phải điểm đã được xác nhận.** Chỉ chốt mức này khi key anchor đúng, GitHub Actions xanh và bộ chấm ẩn đạt. Hiện có thể xác nhận các kiểm tra local trong verification.json; không suy diễn test công khai thành điểm hidden. Nếu một kiểm tra thất bại thì điểm tương ứng chưa chốt. Không dùng bonus để bù.\n\n"+
      f"Kiểm tra local: {sum(x['ok'] for x in verification)}/{len(verification)} lệnh đạt exit code mong đợi.\n\n"+
      "Không sửa src/lab8; không sửa tay reports; giữ nhãn tách rời; chỉ siết/thêm ngưỡng. Bằng chứng cuối cần kiểm tra git diff -- src/lab8.\n\n## Trước khi nộp\n\n1. Chạy từ src: python -m lab9.verify_submission và python -m lab9.build_docs.\n2. Review code/docs, commit baseline v1/v2 cùng file Lab 9 trên starter/d09; không add thư mục starter lồng.\n3. Push nhánh, mở PR vào main; dán PR_LAB9.md, đợi cả eval-gate và eval-gate-v2 xanh.\n4. Nhờ giảng viên đối chiếu anchor/key và chạy hidden; kiểm tra thời hạn trên lớp. README yêu cầu 23:59 ngày học, không suy ra ngày học từ ngày máy.\n")
    public_out="\n\n".join("$ "+r["command"]+"\n"+r["stdout"] for r in verification if any(t in r["command"] for t in ("lab9.gate","lab9.mutation","lab9.traps")))
    Path("../PR_LAB9.md").write_text("# Lab 9: đánh giá, phân tích lỗi và gate chống regression\n\nHoàn thiện M0–M7, giữ nguyên Lab 8; grader tiền, approval, reply/ledger và proposal; bootstrap theo item, slice gate, pass^5, integrity và ratchet.\n\nTài liệu: docs/eval_card.md, docs/trace_case.md, docs/judge_audit.md, docs/PRD_v1.1.md, docs/self_assessment_lab9.md.\n\n## Bằng chứng chạy local\n\n```text\n"+public_out+"\n```\n\nChưa có kết quả GitHub Actions hoặc hidden test tại thời điểm tạo mô tả này. Không tuyên bố điểm chính thức.\n",encoding="utf-8")
    print("Generated trace evidence, taxonomy, audit, eval card, PRD, self-assessment and PR body.")

if __name__=="__main__": main()
