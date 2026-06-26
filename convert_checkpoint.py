"""
Convert PyTorch Lightning CasMVSNet checkpoint to our model format.

Usage:
    python convert_checkpoint.py /path/to/checkpoint.ckpt [output.pth]
"""

import torch
import sys
import os

# Default paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ckpt_path = os.path.join(PROJECT_ROOT, "checkpoints", "_ckpt_epoch_10.ckpt")
output_path = os.path.join(PROJECT_ROOT, "checkpoints", "casmvsnet_dtu.pth")

# Allow command-line override
if len(sys.argv) >= 2:
    ckpt_path = sys.argv[1]
if len(sys.argv) >= 3:
    output_path = sys.argv[2]

print(f"Loading: {ckpt_path}")
ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)

if "state_dict" in ckpt:
    state = ckpt["state_dict"]
elif "model" in ckpt:
    state = ckpt["model"]
else:
    state = ckpt

# Strip "model." prefix, skip non-parameter keys (running stats, optimizers, etc)
new_state = {}
for k, v in state.items():
    key = k.replace("model.", "")
    # Skip optimizer, epoch, batch norm running stats
    if any(key.startswith(p) for p in ("optimizer", "epoch", "global_step", "lr_")):
        continue
    new_state[key] = v

print(f"Checkpoint keys after cleaning: {len(new_state)}")

# Load our model
sys.path.insert(0, PROJECT_ROOT)
from hybridmvs.mvs_network import CasMVSNet

model = CasMVSNet(base_channels=8, feat_channels=32)

our_keys = {k: v.shape for k, v in model.named_parameters()}
print(f"Our model parameters: {len(our_keys)}")

# Map checkpoint keys to our model
matched = 0
skipped = 0
loaded = {}

for our_k, our_shape in our_keys.items():
    ckpt_v = new_state.get(our_k)
    if ckpt_v is not None and ckpt_v.shape == our_shape:
        loaded[our_k] = ckpt_v
        matched += 1
    else:
        skipped += 1
        if skipped <= 5:
            ckpt_shape = list(ckpt_v.shape) if ckpt_v is not None else "MISSING"
            print(f"  skip: {our_k} ours={list(our_shape)} ckpt={ckpt_shape}")

model.load_state_dict(loaded, strict=False)

# Also copy BN running stats (buffers, not parameters).
# named_parameters() skips buffers, so we must copy them explicitly.
bn_copied = 0
for k, v in new_state.items():
    if ('running_mean' in k or 'running_var' in k or 'num_batches_tracked' in k):
        try:
            # Navigate nested attribute path, e.g. "feature.conv0.0.bn.running_mean"
            parts = k.split('.')
            obj = model
            for part in parts[:-1]:
                if part.isdigit():
                    obj = obj[int(part)]
                else:
                    obj = getattr(obj, part)
            attr_name = parts[-1]
            buf = getattr(obj, attr_name)
            if isinstance(buf, torch.Tensor) and buf.shape == v.shape:
                buf.copy_(v)
                bn_copied += 1
        except (AttributeError, IndexError):
            pass

torch.save(model.state_dict(), output_path)
print(f"BN buffers copied: {bn_copied}")

print(f"\nMatched: {matched}/{len(our_keys)}, Skipped: {skipped}")
print(f"Saved: {output_path}")
