# Trace case — C-002@11

Trial: `seeded_regression C-002@11`, report `E-seeded_regression-20261117-3aa2`.
Bước sai đầu tiên là **event 3, model_override**, payload `delay_days=5`.
Event 1 handoff chuyển đúng claim và scope; event 2 investigator đọc đúng DB.
Ticket được dùng để ghi đè delay_days ở event 3, trước khi event 4 quote tính lại tiền.
Ledger ghi **20000 VND**, nhãn là **0 VND**; status `resolved` thay vì `denied`.
Đây là FM-03; quote và refund sau đó là hậu quả của quyết định sai này.

Đối chứng `fixed` trên cùng claim/seed không có override; event 3 quote trả 0,
ledger=0, status=denied, Lab8 grader PASS.
Regression test: `tests/test_lab9_regressions.py::test_lab9_first_wrong_step_ticket_override`.
Test kiểm tra thứ tự 3 event đầu, ledger sai trên biến thể lỗi và ledger đúng trên fixed.

Lệnh tái hiện (từ src):
```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k lab9_first_wrong_step
```
Trace chứng minh hành vi ghi đè và hậu quả trên MockLLM, không chứng minh nguyên nhân suy luận nội bộ của một LLM thật.
