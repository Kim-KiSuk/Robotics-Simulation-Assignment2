import h5py, numpy as np
f = h5py.File('datasets/toy2box_agibot.hdf5', 'r')
D = f['data']
demos = sorted(D, key=lambda k: int(k.split('_')[1]))
print('episodes:', len(demos), '| total:', D.attrs['total'])
for k in demos:
    a = D[k]['actions'][:]
    n = D[k].attrs['num_samples']
    ok = int(D[k].attrs['success'])
    sw = int((np.diff(a[:, 6]) != 0).sum())  # 그리퍼 전환
    idle = (a[:, :6] == 0).all(1).mean()     # 멈춤 비율
    print(f'{k:<8s} len={n:4d} ({n/20:.1f}s) '
          f'sw={sw:2d} idle={idle:.0%} ok={ok}')
