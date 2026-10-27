import torch
from torchvision import models
model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)

feature_extractor = torch.nn.Sequential(*(list(model.children())[:-1]))

dummy = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    feature_extractor,
    dummy,
    "mobilenetv2_feature.onnx",
    input_names=["input"],
    output_names=["features"],
    dynamic_axes={"input": {0: "batch"}, "features": {0: "batch"}},
    opset_version=11
    )
print("생성 완료")
