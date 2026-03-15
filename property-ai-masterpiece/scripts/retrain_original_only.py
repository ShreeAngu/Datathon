#!/usr/bin/env python3
"""
Retrain on ORIGINAL dataset only (real images + original AI-generated fakes).
Excludes Fatimah forensic fakes which have a different signal and hurt accuracy.

Original dataset: ~607 real + 100 AI fakes = 707 images → gave 90.1% val acc
This script filters out fake_fatimah_* and fake_render_* files.

Usage: python scripts/retrain_original_only.py
"""

import sys, json, random, argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import torchvision.transforms as T
from torchvision import models
from tqdm import tqdm

MODEL_DIR = project_root / "backend" / "app" / "models"
DATASET   = project_root / "dataset"


# ---------------------------------------------------------------------------
# Dataset — original fakes only (excludes fatimah/render/pexels/lexica)
# ---------------------------------------------------------------------------
EXCLUDED_FAKE_PREFIXES = (
    "fake_fatimah_",
    "fake_render_",
    "fake_pexels_",
    "fake_lexica_",
    "fake_hf_",
    "fake_sdxl_",
)

class OriginalDataset(Dataset):
    def __init__(self, split: str = "train", seed: int = 42):
        self.split = split
        norm = T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        if split == "train":
            self.transform = T.Compose([
                T.Resize((256, 256)),
                T.RandomCrop(224),
                T.RandomHorizontalFlip(0.5),
                T.RandomRotation(15),
                T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
                T.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.85, 1.15)),
                T.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
                T.ToTensor(), norm,
            ])
        else:
            self.transform = T.Compose([T.Resize((224, 224)), T.ToTensor(), norm])

        exts = {".jpg", ".jpeg", ".png"}
        real_imgs = [p for p in (DATASET / "real").rglob("*") if p.suffix.lower() in exts
                     and "fatimah" not in p.parent.name]  # exclude interior_fatimah dir
        fake_imgs = [p for p in (DATASET / "fake").rglob("*") if p.suffix.lower() in exts
                     and not any(p.name.startswith(pfx) for pfx in EXCLUDED_FAKE_PREFIXES)]

        all_samples = [(str(p), 0) for p in real_imgs] + [(str(p), 1) for p in fake_imgs]
        random.seed(seed)
        random.shuffle(all_samples)

        split_idx = int(len(all_samples) * 0.8)
        self.samples = all_samples[:split_idx] if split == "train" else all_samples[split_idx:]

        n_real = sum(1 for _, l in self.samples if l == 0)
        n_fake = sum(1 for _, l in self.samples if l == 1)
        print(f"📦 {split}: {len(self.samples)} samples  (real={n_real}, fake={n_fake})")

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label, path


# ---------------------------------------------------------------------------
# Model — MobileNetV3-Small (same as original 90.1% model)
# backbone.classifier: Linear(576→256), Hardswish, Dropout, Linear(256→64),
#                      Hardswish, Dropout, Linear(64→2)
# ---------------------------------------------------------------------------
class MobileNetFakeDetector(nn.Module):
    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = models.mobilenet_v3_small(weights=weights)
        in_features = self.backbone.classifier[0].in_features  # 576
        self.backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 64),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 2),
        )

    def forward(self, x): return self.backbone(x)

    def freeze_backbone(self, freeze: bool = True):
        for param in self.backbone.features.parameters():
            param.requires_grad = not freeze


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------
def evaluate(model, loader, criterion, device):
    model.eval()
    loss_sum = correct = total = tp = fp = tn = fn = 0
    with torch.no_grad():
        for imgs, labels, _ in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            out   = model(imgs)
            loss_sum += criterion(out, labels).item()
            preds = out.argmax(1)
            correct += (preds == labels).sum().item()
            total   += labels.size(0)
            tp += ((preds == 1) & (labels == 1)).sum().item()
            fp += ((preds == 1) & (labels == 0)).sum().item()
            fn += ((preds == 0) & (labels == 1)).sum().item()
    acc  = correct / total * 100
    prec = tp / (tp + fp + 1e-9) * 100
    rec  = tp / (tp + fn + 1e-9) * 100
    f1   = 2 * prec * rec / (prec + rec + 1e-9)
    return loss_sum / len(loader), acc, prec, rec, f1


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Training MobileNetV3-Small (original dataset only) on {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    train_ds = OriginalDataset("train")
    val_ds   = OriginalDataset("val")

    n_real = sum(1 for _, l in train_ds.samples if l == 0)
    n_fake = len(train_ds) - n_real
    w_real = len(train_ds) / (2 * n_real + 1e-9)
    w_fake = len(train_ds) / (2 * n_fake + 1e-9)
    class_weights = torch.tensor([w_real, w_fake], dtype=torch.float32).to(device)
    print(f"   Class weights — real: {w_real:.2f}, fake: {w_fake:.2f}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)

    model = MobileNetFakeDetector(pretrained=True)
    model.freeze_backbone(freeze=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.AdamW(model.backbone.classifier.parameters(),
                            lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = 0.0
    patience_ctr = 0
    history      = []

    for epoch in range(args.epochs):
        if epoch == 8:
            print("\n🔓 Unfreezing backbone...")
            model.freeze_backbone(freeze=False)
            optimizer = optim.AdamW([
                {"params": model.backbone.classifier.parameters(), "lr": args.lr},
                {"params": model.backbone.features.parameters(),   "lr": args.lr * 0.05},
            ], weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=args.epochs - epoch)

        model.train()
        t_correct = t_total = 0
        for imgs, labels, _ in tqdm(train_loader,
                                    desc=f"Epoch {epoch+1:02d}/{args.epochs}",
                                    leave=False):
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out  = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            t_correct += (out.argmax(1) == labels).sum().item()
            t_total   += labels.size(0)

        train_acc = t_correct / t_total * 100
        _, val_acc, prec, rec, f1 = evaluate(model, val_loader, criterion, device)

        print(f"Epoch {epoch+1:02d} | train={train_acc:.1f}%  val={val_acc:.1f}%  "
              f"prec={prec:.1f}%  rec={rec:.1f}%  f1={f1:.1f}")
        history.append({"epoch": epoch+1, "train_acc": round(train_acc,2),
                        "val_acc": round(val_acc,2), "f1": round(f1,2)})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_DIR / "fake_detector_best.pt")
            torch.save(model.state_dict(), MODEL_DIR / "fake_detector_final.pt")
            print(f"   💾 New best: {val_acc:.1f}%")
            patience_ctr = 0
        else:
            patience_ctr += 1
            if patience_ctr >= args.patience:
                print(f"⏹  Early stopping at epoch {epoch+1}")
                break

        scheduler.step()

    # Save metadata — mark as mobilenet_v3_small so inference loads correctly
    meta = {
        "model_architecture": "MobileNetV3-Small",
        "training_samples":   len(train_ds),
        "validation_samples": len(val_ds),
        "best_val_accuracy":  round(best_val_acc, 2),
        "batch_size":         args.batch_size,
        "learning_rate":      args.lr,
        "epochs_trained":     len(history),
        "history":            history,
    }
    (MODEL_DIR / "fake_detector_metadata.json").write_text(json.dumps(meta, indent=2))
    # Write arch file so inference auto-detects correctly
    (MODEL_DIR / "fake_detector_arch.txt").write_text("mobilenet_v3_small")

    print(f"\n🎉 Best val accuracy: {best_val_acc:.1f}%")
    if best_val_acc >= 88:
        print("✅ TARGET MET!")
    elif best_val_acc >= 80:
        print("⚠  Good — run test_authenticity.py")
    else:
        print("❌ Below target")
    return best_val_acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int,   default=35)
    parser.add_argument("--batch-size", type=int,   default=16)
    parser.add_argument("--lr",         type=float, default=8e-4)
    parser.add_argument("--patience",   type=int,   default=8)
    train(parser.parse_args())
