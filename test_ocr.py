from paddleocr import PaddleOCR

# 1. 雇佣并唤醒我们的AI图文识别员（首次唤醒时，它会自动从网上下载它的“大脑模型文件”）
# use_angle_cls=True: 开启方向分类器（就算图片里的字是歪的、倒着的，它也能自动扶正再认）
# lang="ch": 告诉它主要识别中文和英文
# 把 use_angle_cls 换成了官方推荐的新名字 use_textline_orientation
ocr = PaddleOCR(use_textline_orientation=True, lang="ch")

# 2. 把测试图片的路径交给它，让它开始干活
img_path = "C:/Users/86734/Pictures/Screenshots/屏幕截图 2024-11-30 212349.png"
result = ocr.ocr(img_path, cls=True)

# 3. 扒开它的脑子，看看它到底输出了什么原始数据
for line in result[0]:
    print(line)