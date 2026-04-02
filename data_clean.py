from paddleocr import PaddleOCR

ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
img_path = "C:/Users/86734/Pictures/Screenshots/屏幕截图 2024-11-30 212349.png"
result = ocr.ocr(img_path)

print("\n--- 👇 下面是为您提取的纯文本 👇 ---\n")

# 遍历那堆复杂的原始结果
for line in result[0]:
    # 极客小课堂：数据结构解剖
    # 此时的 line 长这样：[[坐标], ('文字', 置信度)]
    # line[1] 意思是：跳过坐标，只拿第2个元素，也就是小括号 ('文字', 置信度)
    # line[1][0] 意思是：在小括号里，再拿第1个元素，也就是纯 '文字'！
    text = line[1][0]

    print(text)