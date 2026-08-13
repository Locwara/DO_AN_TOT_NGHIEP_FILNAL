import re

with open('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh/quyen_bao_cao/so_lieu_benchmark_sandbox_jmeter.md', 'r') as f:
    text = f.read()

# Toning down absolute terms
replacements = {
    "cực kỳ mượt mà": "ổn định",
    "cực nhanh": "nhanh",
    "hoàn toàn không gặp khó khăn": "hoạt động tốt",
    "triệt để bài toán": "tốt bài toán",
    "bỏ qua hoàn toàn": "bỏ qua phần lớn",
    "hoàn tất trọn vẹn": "hoàn thành",
    "không ghi nhận bất kỳ một lỗi nào": "không ghi nhận lỗi",
    "hoàn toàn không bị sập hay cạn kiệt tài nguyên": "duy trì hoạt động ổn định và không gặp tình trạng thiếu hụt tài nguyên",
    "hoàn toàn có thể chấp nhận được": "phù hợp",
    "hoàn toàn có khả năng": "có khả năng",
    "bình an vô sự": "hoạt động bình thường",
    "vắt kiệt": "tiêu thụ hết",
    "sập (Crash)": "gián đoạn dịch vụ",
    "cực lớn": "cao",
}

for k, v in replacements.items():
    text = text.replace(k, v)

with open('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh/quyen_bao_cao/so_lieu_benchmark_sandbox_jmeter.md', 'w') as f:
    f.write(text)
