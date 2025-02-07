import torch
import numpy as np

@torch.no_grad()
def warp_kpts(kpts0, depth0, depth1, T_0to1, K0, K1):
    """ Warp kpts0 from I0 to I1 with depth, K and Rt
    Also check covisibility and depth consistency.
    Depth is consistent if relative error < 0.2 (hard-coded).
    
    Args:
        kpts0 (torch.Tensor): [N, L, 2] - <x, y>,
        depth0 (torch.Tensor): [N, H, W],
        depth1 (torch.Tensor): [N, H, W],
        T_0to1 (torch.Tensor): [N, 3, 4],
        K0 (torch.Tensor): [N, 3, 3],
        K1 (torch.Tensor): [N, 3, 3],
    Returns:
        calculable_mask (torch.Tensor): [N, L]
        warped_keypoints0 (torch.Tensor): [N, L, 2] <x0_hat, y1_hat>
    """
    kpts0_long = kpts0.round().long()

    # Sample depth, get calculable_mask on depth != 0
    kpts0_depth = torch.stack(
        [depth0[i, kpts0_long[i, :, 1], kpts0_long[i, :, 0]] for i in range(kpts0.shape[0])], dim=0
    )  # (N, L)
    nonzero_mask = kpts0_depth != 0

    # Unproject
    kpts0_h = torch.cat([kpts0, torch.ones_like(kpts0[:, :, [0]])], dim=-1) * kpts0_depth[..., None]  # (N, L, 3)
    kpts0_cam = K0.inverse() @ kpts0_h.transpose(2, 1)  # (N, 3, L)

    # Rigid Transform
    w_kpts0_cam = T_0to1[:, :3, :3] @ kpts0_cam + T_0to1[:, :3, [3]]    # (N, 3, L)
    w_kpts0_depth_computed = w_kpts0_cam[:, 2, :]

    # Project
    w_kpts0_h = (K1 @ w_kpts0_cam).transpose(2, 1)  # (N, L, 3)
    w_kpts0 = w_kpts0_h[:, :, :2] / (w_kpts0_h[:, :, [2]] + 1e-4)  # (N, L, 2), +1e-4 to avoid zero depth

    # Covisible Check
    h, w = depth1.shape[1:3]
    covisible_mask = (w_kpts0[:, :, 0] > 0) * (w_kpts0[:, :, 0] < w-1) * \
        (w_kpts0[:, :, 1] > 0) * (w_kpts0[:, :, 1] < h-1)
    w_kpts0_long = w_kpts0.long()
    w_kpts0_long[~covisible_mask, :] = 0

    w_kpts0_depth = torch.stack(
        [depth1[i, w_kpts0_long[i, :, 1], w_kpts0_long[i, :, 0]] for i in range(w_kpts0_long.shape[0])], dim=0
    )  # (N, L)
    consistent_mask = ((w_kpts0_depth - w_kpts0_depth_computed) / w_kpts0_depth).abs() < 0.2
    valid_mask = nonzero_mask * covisible_mask * consistent_mask

    return valid_mask, w_kpts0


def make_homog(points):
    """ 将点集(dimxn 的数组)转换为齐次坐标表示 """
    return np.vstack((points,np.ones((1,points.shape[1]))))

def normalize(points):
    """ 在齐次坐标意义下，对点集进行归一化，使最后一行为 1 """
    for row in points:
        row /= row[-1]
    return points

@torch.no_grad()
def warp_kpts_ptb(kpts0, homo):
    kpts0_long = kpts0.round().long()
    kpts = kpts0_long.cpu().numpy()
    kpts_m = make_homog(kpts[0].T)
    homo = homo[0].cpu().numpy()
    kpts_warped = np.dot(homo,kpts_m).T
    kpts_warped = normalize(kpts_warped)
    kpts_warped = np.delete(kpts_warped, -1, axis=1)
    kpts0_w = kpts_warped.reshape(1, kpts_warped.shape[0], kpts_warped.shape[1])
    #print(kpts0_w)
    #print(kpts0)
    kpts0_w = torch.from_numpy(kpts0_w).cuda()
    return kpts0_w

@torch.no_grad()
def warp_kpts_ptb_inv(kpts0, homo):
    kpts0_long = kpts0.round().long()
    kpts = kpts0_long.cpu().numpy()
    kpts_m = make_homog(kpts[0].T)
    homo = homo[0].cpu().numpy()
    homo = np.linalg.inv(homo)
    kpts_warped = np.dot(homo,kpts_m).T
    kpts_warped = normalize(kpts_warped)
    kpts_warped = np.delete(kpts_warped, -1, axis=1)
    kpts0_w = kpts_warped.reshape(1, kpts_warped.shape[0], kpts_warped.shape[1])
    #print(kpts0_w)
    #print(kpts0)
    kpts0_w = torch.from_numpy(kpts0_w).cuda()
    return kpts0_w

