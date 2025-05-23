import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import os
from uvars import xfn, yfn




class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 1, 3, padding=1)
        )

    def forward(self, x):
        return self.encoder(x)

class RasterPatchDataset(Dataset):
    def __init__(self, x_img, y_img, patch_size=64, num_patches=10000):
        self.patch_size = patch_size
        self.x_img = x_img
        self.y_img = y_img
        self.valid_mask = (~np.isnan(x_img)) & (~np.isnan(y_img))
        self.coords = np.argwhere(self.valid_mask)
        self.num_patches = num_patches

    def __len__(self):
        return self.num_patches

    def __getitem__(self, idx):
        h, w = self.x_img.shape
        while True:
            yx = self.coords[np.random.randint(len(self.coords))]
            y, x = yx
            if y < self.patch_size or y >= h - self.patch_size or x < self.patch_size or x >= w - self.patch_size:
                continue
            yp = slice(y - self.patch_size//2, y + self.patch_size//2)
            xp = slice(x - self.patch_size//2, x + self.patch_size//2)
            x_patch = self.x_img[yp, xp]
            y_patch = self.y_img[yp, xp]
            if np.isnan(x_patch).any() or np.isnan(y_patch).any():
                continue
            return (torch.tensor(x_patch[None], dtype=torch.float32),
                    torch.tensor(y_patch[None], dtype=torch.float32))



# Load and align rasters
with rasterio.open(xfn) as src_x:
    x_data = src_x.read(1)
    x_profile = src_x.profile
    x_transform = src_x.transform

with rasterio.open(yfn) as src_y:
    y_data = src_y.read(1)
    y_resampled = np.empty_like(x_data)
    reproject(
        source=y_data,
        destination=y_resampled,
        src_transform=src_y.transform,
        src_crs=src_y.crs,
        dst_transform=x_transform,
        dst_crs=src_x.crs,
        resampling=Resampling.bilinear
    )

# Normalize inputs
x_data = (x_data - np.nanmean(x_data)) / np.nanstd(x_data)
y_data = y_resampled

# Create dataset
train_dataset = RasterPatchDataset(x_data, y_data, patch_size=64, num_patches=20000)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
model = SimpleCNN().to(device)
optimizer = optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.MSELoss()

for epoch in range(5):
    model.train()
    total_loss = 0
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        pred = model(xb)
        loss = loss_fn(pred, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {epoch+1}, Loss: {total_loss / len(train_loader):.4f}")



patch_size = 64
stride = 64
h, w = x_data.shape
pred_map = np.full((h, w), np.nan)
counts = np.zeros((h, w))

model.eval()
with torch.no_grad():
    for i in range(0, h - patch_size + 1, stride):
        for j in range(0, w - patch_size + 1, stride):
            x_patch = x_data[i:i+patch_size, j:j+patch_size]
            if np.isnan(x_patch).any():
                continue
            x_tensor = torch.tensor(x_patch[None, None], dtype=torch.float32).to(device)
            y_pred = model(x_tensor).cpu().numpy().squeeze()
            pred_map[i:i+patch_size, j:j+patch_size] = np.nan_to_num(pred_map[i:i+patch_size, j:j+patch_size]) + y_pred
            counts[i:i+patch_size, j:j+patch_size] += 1

pred_map[counts > 0] /= counts[counts > 0]


output_path = os.path.join(os.path.dirname(xfn), 'predicted_cnn.tif')
with rasterio.open(output_path, 'w', **x_profile) as dst:
    dst.write(pred_map.astype(x_profile['dtype']), 1)

print(f"CNN output saved to: {output_path}")


