#!/usr/bin/env python3

import os
import argparse

import numpy as np
import nibabel as nib
from sklearn.metrics import auc

def load_nifti_data(filepath):
    """Load a NIfTI file using nibabel and return its data as a NumPy array."""
    img = nib.load(filepath)
    return img.get_fdata()

def compute_tpr_fpr(gt_data, pred_data, mask_data):
    """
    Compute TPR and FPR for a single binary prediction compared to ground truth,
    restricted to voxels where mask_data == 1.
    Both gt_data and pred_data are expected to contain 0 or 1 only.
    """
    # Restrict to the masked region
    mask_indices = mask_data == 1

    # Flatten the relevant voxels
    gt = gt_data[mask_indices].flatten()
    pred = pred_data[mask_indices].flatten()

    # Compute confusion matrix components
    tp = np.sum((pred == 1) & (gt == 1))
    tn = np.sum((pred == 0) & (gt == 0))
    fp = np.sum((pred == 1) & (gt == 0))
    fn = np.sum((pred == 0) & (gt == 1))

    # Avoid division by zero
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    return tpr, fpr

def main():
    parser = argparse.ArgumentParser(description="Evaluate submission NIfTI files (binary 0/1) vs. ground truth.")
    parser.add_argument("--mask-file", required=True, help="Path to the NIfTI mask file.")
    parser.add_argument("--gt-file", required=True, help="Path to the NIfTI ground-truth file (binary 0/1).")
    parser.add_argument("--submission-folder", required=True, help="Folder containing participant NIfTI predictions.")
    parser.add_argument("--output-plot", default="roc_curve.png", help="Filename for the saved ROC curve plot.")
    parser.add_argument("--output-stats", default="results.txt", help="Filename to save the computed AUC and points.")
    parser.add_argument("--threshold", type=float, default=0.3, help="Threshold for fpr.")

    args = parser.parse_args()

    # 1. Load mask and ground truth data
    mask_data = load_nifti_data(args.mask_file)
    gt_data = load_nifti_data(args.gt_file)

    # 2. Iterate over all NIfTI files in the submissions folder
    submission_files = [
        f for f in os.listdir(args.submission_folder)
        if f.lower().endswith(".nii") or f.lower().endswith(".nii.gz")
    ]

    # Lists to store all TPR/FPR points
    tpr_list = []
    fpr_list = []

    for sub_file in submission_files:
        sub_path = os.path.join(args.submission_folder, sub_file)
        pred_data = load_nifti_data(sub_path)

        # 3. Compute TPR and FPR for this submission
        tpr, fpr = compute_tpr_fpr(gt_data, pred_data, mask_data)
        if fpr>0.3:
            continue
        tpr_list.append(tpr)
        fpr_list.append(fpr)
        
        print(f"File: {sub_file} => TPR={tpr:.3f}, FPR={fpr:.3f}")

    # 4. Sort the points by FPR (typical approach for computing AUC in ROC space)
    #    Each submission is a single threshold => each is a single point
    #    We'll form a piecewise curve from these points.
    points = sorted(zip(fpr_list, tpr_list), key=lambda x: x[0])
    sorted_fprs = [p[0] for p in points]
    sorted_tprs = [p[1] for p in points]

    # 5. Compute area under the curve (AUC) using a standard trapezoidal rule
    #    from scikit-learn
    roc_auc = auc(sorted_fprs, sorted_tprs)
    return roc_auc

if __name__ == "__main__":
    main()
