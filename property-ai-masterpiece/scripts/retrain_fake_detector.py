#!/usr/bin/env python3
"""
Retrain fake detector (EfficientNet-B0) on expanded 3299-image dataset.
Saves to: fake_detector_best.pt  (best val acc checkpoint)
          fake_detector_final.pt (last epoch)

Usage: python scripts/retrain_fake_detector.py [--epochs 50] [--batch-size 16]
"""

import sys, json, argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
from torchvision import models

from backend.app.data.fake_detection_dataset import FakeDetectionDataset

MODEL_DIR = project_root / "backend" / "app" / "models"


# ---------------------------------------------------------------------------
# EfficientNet-B0 — matches fake_detector_inference.py _EfficientNetWrapper
# backbone.classifier: Dropout → Linear(1280→256) → SiLU → Dropout → Linear(256→2)
# ---------------------------------------------------------------------------
class EfficientFakeDetector(nn.Module):
    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = models.efficientnet_b0(weights=weights)
        in_features = self.backbone.classifier[1].in_features  # 1280
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 256),
            nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 2),
        )

    def forward(self, x):
        return self.backbone(x)

    def freeze_backbone(self, freeze: bool = True):
        for name, param in self.backbone.named_parameters():
            if "classifier" not in name:
                param.requires_grad = not freeze


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate(model, loader, criterion, device):
    model.eval()
    loss_sum = correct = total = tp = fp = tn = fn = 0
    with torch.no_grad():
        for imgs, labels, _ in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            out   = model(imgs)
            loss_sum += criterion(out, labels).item()
            preds = out.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total   += labels.size(0)
            tp += ((preds == 1) & (labels == 1)).sum().item()
            fp += ((preds == 1) & (labels == 0)).sum().item()
            tn += ((preds == 0) & (labels == 0)).sum().item()
            fn += ((preds == 0) & (labels == 1)).sum().item()

    acc       = correct / total * 100
    precision = tp / (tp + fp + 1e-9) * 100
    recall    = tp / (tp + fn + 1e-9) * 100
    f1        = 2 * precision * recall / (precision + recall + 1e-9)
    return loss_sum / len(loader), acc, precision, recall, f1


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Training EfficientNet-B0 on {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    train_ds = FakeDetectionDataset(str(project_root / "dataset"), split="train")
    val_ds   = FakeDetectionDataset(str(project_root / "dataset"), split="val")

    # Class weights from sample list (fast, no __getitem__ calls)
    n_real = sum(1 for _, l in train_ds.samples if l == 0)
    n_fake = sum(1 for _, l in train_ds.samples if l == 1)
    w_real = len(train_ds) / (2 * n_real + 1e-9)
    w_fake = len(train_ds) / (2 * n_fake + 1e-9)
    class_weights = torch.tensor([w_real, w_fake], dtype=torch.float32).to(device)
    print(f"   Train: {len(train_ds)} (real={n_real}, fake={n_fake})")
    print(f"   Val  : {len(val_ds)}")
    print(f"   Class weights — real: {w_real:.2f}, fake: {w_fake:.2f}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)

    model = EfficientFakeDetector(pretrained=True)
    model.freeze_backbone(freeze=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.05)

    # Phase 1: train head only
    optimizer = optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr, weight_decay=1e-4,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = 0.0
    patience_ctr = 0
    history      = []

    for epoch in range(args.epochs):

        # Phase 2: unfreeze backbone at epoch 8
        if epoch == 8:
            print("\n🔓 Unfreezing backbone for full fine-tuning...")
            model.freeze_backbone(freeze=False)
            optimizer = optim.AdamW([
                {"params": [p for n, p in model.backbone.named_parameters()
                            if "classifier" in n],     "lr": args.lr},
                {"params": [p for n, p in model.backbone.named_parameters()
                            if "classifier" not in n], "lr": args.lr * 0.02},
            ], weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=args.epochs - epoch)

        # Train
        model.train()
        t_loss = t_correct = t_total = 0
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
            t_loss    += loss.item()
            t_correct += (out.argmax(1) == labels).sum().item()
            t_total   += labels.size(0)

        train_acc = t_correct / t_total * 100
        _, val_acc, prec, rec, f1 = evaluate(model, val_loader, criterion, device)

        print(f"Epoch {epoch+1:02d} | "
              f"train={train_acc:.1f}%  val={val_acc:.1f}%  "
              f"prec={prec:.1f}%  rec={rec:.1f}%  f1={f1:.1f}")

        history.append({"epoch": epoch+1, "train_acc": round(train_acc, 2),
                        "val_acc": round(val_acc, 2), "f1": round(f1, 2)})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_DIR / "fake_detector_best.pt")
            print(f"   💾 New best: {val_acc:.1f}%")
            patience_ctr = 0
        else:
            patience_ctr += 1
            if patience_ctr >= args.patience:
                print(f"⏹  Early stopping at epoch {epoch+1}")
                break

        scheduler.step()

    # Save final checkpoint + metadata
    torch.save(model.state_dict(), MODEL_DIR / "fake_detector_final.pt")
    meta = {
        "model_architecture": "EfficientNet-B0",
        "training_samples":   len(train_ds),
        "validation_samples": len(val_ds),
        "best_val_accuracy":  round(best_val_acc, 2),
        "batch_size":         args.batch_size,
        "learning_rate":      args.lr,
        "epochs_trained":     len(history),
        "history":            history,
    }
    (MODEL_DIR / "fake_detector_metadata.json").write_text(json.dumps(meta, indent=2))

    print(f"\n🎉 Best val accuracy: {best_val_acc:.1f}%")
    if best_val_acc >= 90:
        print("✅ TARGET MET — 90%+ achieved!")
    elif best_val_acc >= 85:
        print("⚠  Good — run test_authenticity.py to check test accuracy")
    else:
        print("❌ Below target — check class balance")

    return best_val_acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int,   default=50)
    parser.add_argument("--batch-size", type=int,   default=16)
    parser.add_argument("--lr",         type=float, default=8e-4)
    parser.add_argument("--patience",   type=int,   default=10)
    train(parser.parse_args())
