from transformers import CLIPModel, CLIPProcessor
from PIL import Image
import torch

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

img = Image.open("dataset/uploads/76a58247d43b4a58b4015ed8ea144ccb.jpeg").convert("RGB")
inputs = processor(images=img, return_tensors="pt")

with torch.no_grad():
    outputs = model.get_image_features(pixel_values=inputs['pixel_values'])

print("Type:", type(outputs))
print("Is tensor:", isinstance(outputs, torch.Tensor))
if isinstance(outputs, torch.Tensor):
    print("Shape:", outputs.shape)
    print("First 10:", outputs[0, :10])
else:
    print("Keys:", list(outputs.keys()) if hasattr(outputs, 'keys') else 'no keys')
