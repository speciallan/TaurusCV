import numpy as np


def anchor_targets_bbox(image_shape,
                        annotations,
                        num_classes,
                        mask_shape=None,
                        negative_overlap=0.4,
                        positive_overlap=0.5,
                        **kwargs):
    anchors = anchors_for_shape(image_shape, **kwargs)

    # label: 1 è positivo, 0 è negativo, -1 è ignora
    labels = np.ones((anchors.shape[0], num_classes)) * -1

    if annotations.shape[0]:
        # ottiene gli indici dei ground truth con la massima sovrapposizione
        overlaps = compute_overlap(anchors, annotations[:, :4])
        argmax_overlaps_inds = np.argmax(overlaps, axis=1)
        max_overlaps = overlaps[np.arange(overlaps.shape[0]), argmax_overlaps_inds]

        # assegna per prime le label del background in modo che le label positive possano poi oscurarle
        labels[max_overlaps < negative_overlap, :] = 0

        # calcola i box dei target di regressione
        annotations = annotations[argmax_overlaps_inds]

        # ottiene le label di primo piano che superano un certo threshold di IOU
        positive_indices = max_overlaps >= positive_overlap
        labels[positive_indices, :] = 0
        labels[positive_indices, annotations[positive_indices, 4].astype(int)] = 1
    else:
        # se non ci sono annotazioni, allora è tutto considerato background
        labels[:] = 0
        annotations = np.zeros_like(anchors)

    # ignora le annotazioni che finiscono fuori dall'immagine
    mask_shape = image_shape if mask_shape is None else mask_shape
    anchors_centers = np.vstack([(anchors[:, 0] + anchors[:, 2]) / 2, (anchors[:, 1] + anchors[:, 3]) / 2]).T
    indices = np.logical_or(anchors_centers[:, 0] >= mask_shape[1], anchors_centers[:, 1] >= mask_shape[0])
    labels[indices, :] = -1

    return labels, annotations, anchors


def anchors_for_shape(image_shape,
                      pyramid_levels=None,
                      ratios=None,
                      scales=None,
                      strides=None,
                      sizes=None):
    if pyramid_levels is None:
        pyramid_levels = [3, 4, 5, 6, 7]
    if strides is None:
        strides = [2 ** x for x in pyramid_levels]
    if sizes is None:
        sizes = [2 ** (x + 2) for x in pyramid_levels]
    if ratios is None:
        ratios = np.array([0.5, 1, 2])
    if scales is None:
        scales = np.array([2 ** 0, 2 ** (1.0 / 3.0), 2 ** (2.0 / 3.0)])

    # salta i primi due livelli
    image_shape = np.array(image_shape[:2])
    for i in range(pyramid_levels[0] - 1):
        image_shape = (image_shape + 1) // 2

    # calcola gli anchor su tutti i livelli piramidali
    all_anchors = np.zeros((0, 4))
    for idx, p in enumerate(pyramid_levels):
        image_shape = (image_shape + 1) // 2
        anchors = generate_anchors(base_size=sizes[idx], ratios=ratios, scales=scales)
        shifted_anchors = shift(image_shape, strides[idx], anchors)
        all_anchors = np.append(all_anchors, shifted_anchors, axis=0)

    return all_anchors


def shift(shape, stride, anchors):
    shift_x = (np.arange(0, shape[1]) + 0.5) * stride
    shift_y = (np.arange(0, shape[0]) + 0.5) * stride

    shift_x, shift_y = np.meshgrid(shift_x, shift_y)

    shifts = np.vstack((
        shift_x.ravel(), shift_y.ravel(),
        shift_x.ravel(), shift_y.ravel()
    )).transpose()

    A = anchors.shape[0]
    K = shifts.shape[0]
    all_anchors = (anchors.reshape((1, A, 4)) + shifts.reshape((1, K, 4)).transpose((1, 0, 2)))
    all_anchors = all_anchors.reshape((K * A, 4))

    return all_anchors


def generate_anchors(base_size=16, ratios=None, scales=None):

    if ratios is None:
        ratios = np.array([0.5, 1, 2])

    if scales is None:
        scales = np.array([2 ** 0, 2 ** (1.0 / 3.0), 2 ** (2.0 / 3.0)])

    num_anchors = len(ratios) * len(scales)

    # inizializza gli output anchor
    anchors = np.zeros((num_anchors, 4))

    # scala usando la base_size
    anchors[:, 2:] = base_size * np.tile(scales, (2, len(ratios))).T

    # calcola le aree degli anchor
    areas = anchors[:, 2] * anchors[:, 3]

    # corregge in base ai ratios
    anchors[:, 2] = np.sqrt(areas / np.repeat(ratios, len(scales)))
    anchors[:, 3] = anchors[:, 2] * np.repeat(ratios, len(scales))

    # transform from (x_ctr, y_ctr, w, h) -> (x1, y1, x2, y2)
    anchors[:, 0::2] -= np.tile(anchors[:, 2] * 0.5, (2, 1)).T
    anchors[:, 1::2] -= np.tile(anchors[:, 3] * 0.5, (2, 1)).T

    return anchors


def bbox_transform(anchors, gt_boxes, mean=None, std=None):
    # calcola i bounding box dei target di regressione per una immagine
    if mean is None:
        mean = np.array([0, 0, 0, 0])
    if std is None:
        std = np.array([0.1, 0.1, 0.2, 0.2])

    if isinstance(mean, (list, tuple)):
        mean = np.array(mean)
    elif not isinstance(mean, np.ndarray):
        raise ValueError('La media deve essereun np.ndarray, una lista o una tupla. Ricevuto: {}'.format(type(mean)))

    if isinstance(std, (list, tuple)):
        std = np.array(std)
    elif not isinstance(std, np.ndarray):
        raise ValueError('La deviazione standard deve essere un np.ndarray, una lista o una tupla. Ricevuto: {}'.format(type(std)))

    anchor_widths = anchors[:, 2] - anchors[:, 0] + 1.0
    anchor_heights = anchors[:, 3] - anchors[:, 1] + 1.0
    anchor_ctr_x = anchors[:, 0] + 0.5 * anchor_widths
    anchor_ctr_y = anchors[:, 1] + 0.5 * anchor_heights

    gt_widths = gt_boxes[:, 2] - gt_boxes[:, 0] + 1.0
    gt_heights = gt_boxes[:, 3] - gt_boxes[:, 1] + 1.0
    gt_ctr_x = gt_boxes[:, 0] + 0.5 * gt_widths
    gt_ctr_y = gt_boxes[:, 1] + 0.5 * gt_heights

    targets_dx = (gt_ctr_x - anchor_ctr_x) / anchor_widths
    targets_dy = (gt_ctr_y - anchor_ctr_y) / anchor_heights
    targets_dw = np.log(gt_widths / anchor_widths)
    targets_dh = np.log(gt_heights / anchor_heights)

    targets = np.stack((targets_dx, targets_dy, targets_dw, targets_dh))
    targets = targets.T

    targets = (targets - mean) / std

    return targets


def compute_overlap(a, b):
    # calcola la sovrapposizione
    area = (b[:, 2] - b[:, 0] + 1) * (b[:, 3] - b[:, 1] + 1)

    iw = np.minimum(np.expand_dims(a[:, 2], axis=1), b[:, 2]) - np.maximum(np.expand_dims(a[:, 0], 1), b[:, 0]) + 1
    ih = np.minimum(np.expand_dims(a[:, 3], axis=1), b[:, 3]) - np.maximum(np.expand_dims(a[:, 1], 1), b[:, 1]) + 1

    iw = np.maximum(iw, 0)
    ih = np.maximum(ih, 0)

    ua = np.expand_dims((a[:, 2] - a[:, 0] + 1) * (a[:, 3] - a[:, 1] + 1), axis=1) + area - iw * ih

    ua = np.maximum(ua, np.finfo(float).eps)

    intersection = iw * ih

    return intersection / ua
