#!/usr/bin/env python3
"""
Train fake image detector via transfer learning on local dataset.
Usage: python scripts/train_fake_detector.py --epochs 25 --batch-size 16
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

from backend.app.data.fake_detection_dataset import FakeDetectionDataset
from backend.app.models.fake_detector_model import FakeImageClassifier

MODEL_DIR = project_root / "backend" / "app" / "models"


def evaluate(model, loader, criterion, device):
    model.eval()
    loss_sum = correct = total = 0
    tp = fp = tn = fn = 0
    with torch.no_grad():
        for imgs, labels, _ in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            out  = model(imgs)
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


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Training on {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    train_ds = FakeDetectionDataset("dataset", split="train")
    val_ds   = FakeDetectionDataset("dataset", split="val")

    # Compute class weights to handle imbalance (470 real vs 100 fake)
    n_real = sum(1 for _, l, *_ in [train_ds[i] for i in range(len(train_ds))] if l == 0)
    n_fake = len(train_ds) - n_real
    w_real = len(train_ds) / (2 * n_real + 1e-9)
    w_fake = len(train_ds) / (2 * n_fake + 1e-9)
    class_weights = torch.tensor([w_real, w_fake], dtype=torch.float32).to(device)
    print(f"   Class weights — real: {w_real:.2f}, fake: {w_fake:.2f}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)

    model = FakeImageClassifier(pretrained=True)
    model.freeze_backbone(freeze=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.AdamW(model.backbone.classifier.parameters(),
                            lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc  = 0.0
    patience_ctr  = 0
    history       = []

    for epoch in range(args.epochs):
        # Unfreeze backbone at epoch 8 for full fine-tuning
        if epoch == 8:
            print("\n🔓 Unfreezing backbone for full fine-tuning...")
            model.freeze_backbone(freeze=False)
            optimizer = optim.AdamW([
                {"params": model.backbone.classifier.parameters(), "lr": args.lr},
                {"params": model.backbone.features.parameters(),   "lr": args.lr * 0.05},
            ], weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=args.epochs - epoch)

        # Train
        model.train()
        t_loss = t_correct = t_total = 0
        for imgs, labels, _ in tqdm(train_loader,
                                    desc=f"Epoch {epoch+1:02d}/{args.epochs} [Train]",
                                    leave=False):
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out  = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            t_loss    += loss.item()
            t_correct += (out.argmax(1) == labels).sum().item()
            t_total   += labels.size(0)

        train_acc = t_correct / t_total * 100
        val_loss, val_acc, prec, rec, f1 = evaluate(model, val_loader, criterion, device)

        print(f"Epoch {epoch+1:02d} | "
              f"train_acc={train_acc:.1f}%  val_acc={val_acc:.1f}%  "
              f"prec={prec:.1f}%  rec={rec:.1f}%  f1={f1:.1f}")

        history.append({"epoch": epoch+1, "train_acc": train_acc,
                         "val_acc": val_acc, "f1": f1})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_DIR / "fake_detector_best.pt")
            print(f"   💾 New best saved ({val_acc:.1f}%)")
            patience_ctr = 0
        else:
            patience_ctr += 1
            if patience_ctr >= args.patience:
                print(f"⏹️  Early stopping after {epoch+1} epochs")
                break

        scheduler.step()

    # Save final + metadata
    torch.save(model.state_dict(), MODEL_DIR / "fake_detector_final.pt")
    meta = {
        "model_architecture": "MobileNetV3-Small",
        "training_samples":   len(train_ds),
        "validation_samples": len(val_ds),
        "best_val_accuracy":  round(best_val_acc, 2),
        "batch_size":         args.batch_size,
        "learning_rate":      args.lr,
        "history":            history,
    }
    with open(MODEL_DIR / "fake_detector_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n🎉 Done! Best val accuracy: {best_val_acc:.1f}%")
    if best_val_acc >= 85:
        print("✅ EXCELLENT — ready for demo!")
    elif best_val_acc >= 75:
        print("⚠️  Good — consider more epochs if time allows")
    else:
        print("❌ Below target — check class balance and augmentation")
    return best_val_acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int,   default=25)
    parser.add_argument("--batch-size", type=int,   default=16)
    parser.add_argument("--lr",         type=float, default=1e-3)
    parser.add_argument("--patience",   type=int,   default=7)
    train(parser.parse_args())
