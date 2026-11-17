# Judge audit

FAIL là lớp dương; floors κ≥0.6, P≥0.8, R≥0.7.

| Judge | n | κ | P | R | TP/FP/FN/TN | Quyết định |
|---|---|---|---|---|---|---|
| tone | 100 | 0.757 | 0.857 | 0.8 | {'tp': 24, 'fp': 4, 'fn': 6, 'tn': 66} | Dùng trong phạm vi tone replay |
| helpful | 100 | 0.375 | 1.0 | 0.3 | {'tp': 9, 'fp': 0, 'fn': 21, 'tn': 70} | Loại khỏi gate |

## Audit 5 bất đồng

| Case | Reply | Human | Judge | Nhận định | Sửa rubric |
|---|---|---|---|---|---|
| H-008 | Em đã hoàn tiền cho anh rồi nha, anh check giúp em. | FAIL | PASS | Theo nhãn người được cung cấp | Cấm xưng em/anh tùy tiện, nha và check trong chuẩn CSKH; thêm ví dụ âm. |
| H-017 | Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha. | FAIL | PASS | Theo nhãn người được cung cấp | Không đánh đồng có từ Dạ với lịch sự; kiểm tra toàn câu, loại bạn ơi/nha. |
| H-029 | Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm. | FAIL | PASS | Theo nhãn người được cung cấp | Chấm FAIL câu ra lệnh hoặc ngăn khách nhắn thêm; thêm hard negative. |
| H-042 | Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ. | PASS | FAIL | Theo nhãn người được cung cấp | Không bắt buộc lời xin lỗi nếu đã xử lý xong; câu ngắn có thông tin vẫn PASS. |
| H-051 | Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ. | PASS | FAIL | Theo nhãn người được cung cấp | Không chấm FAIL chỉ vì từ refund; glossary cho phép từ chuyên môn nếu lịch sự. |

Tone: tỷ lệ lỗi quan sát 0.28 → Rogan–Gladen 0.3. Helpful: 0.09 → 0.3; recall thấp bỏ sót 21/30 lỗi, nên precision=1 không đủ để dùng gate. Các sửa rubric là đề xuất sau audit, chưa tuyên bố đã đánh giá một judge mới. Tất cả nhãn người là nhãn đi kèm CSV, chưa có hội đồng độc lập tái gán nhãn. Tiền và approval luôn dùng code. Replay công khai chưa chứng minh tổng quát hóa trên held-out.
