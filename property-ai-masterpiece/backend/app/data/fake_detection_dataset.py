"""Dataset loader for real vs fake image classification."""

import os
import random
from pathlib import Path
from torch.utils.data import Dataset
from PIL import Image
import torchvision.transforms as T


class FakeDetectionDataset(Dataset):
    """
    Labels: 0 = Real, 1 = Fake
    Recursively scans subdirectories so real/living_room/*.jpg etc. all get picked up.
    """

    def __init__(self, root_dir: str, split: str = "train", transform=None, seed: int = 42):
        self.root_dir  = root_dir
        self.split     = split
        self.transform = transform or self._default_transform()
        self.samples   = []
        self._load(seed)

    def _default_transform(self):
        norm = T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        if self.split == "train":
            return T.Compose([
                T.Resize((256, 256)),
                T.RandomCrop(224),
                T.RandomHorizontalFlip(0.5),
                T.RandomVerticalFlip(0.1),
                T.RandomRotation(15),
                T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
                T.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.85, 1.15)),
                T.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
                T.RandomGrayscale(p=0.05),
                T.ToTensor(), norm,
            ])
        return T.Compose([T.Resize((224, 224)), T.ToTensor(), norm])

    def _load(self, seed: int):
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        real_dir = Path(self.root_dir) / "real"
        fake_dir = Path(self.root_dir) / "fake"

        real_imgs = [p for p in real_dir.rglob("*") if p.suffix.lower() in exts]
        fake_imgs = [p for p in fake_dir.rglob("*") if p.suffix.lower() in exts]

        all_samples = [(str(p), 0) for p in real_imgs] + [(str(p), 1) for p in fake_imgs]
        random.seed(seed)
        random.shuffle(all_samples)

        split_idx = int(len(all_samples) * 0.8)
        self.samples = all_samples[:split_idx] if self.split == "train" else all_samples[split_idx:]

        n_real = sum(1 for _, l in self.samples if l == 0)
        n_fake = sum(1 for _, l in self.samples if l == 1)
        print(f"📦 {self.split}: {len(self.samples)} samples  (real={n_real}, fake={n_fake})")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label, path
