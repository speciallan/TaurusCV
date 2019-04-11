#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author:Speciallan

"""
用来生成原始anchor
"""

import tensorflow as tf
import keras
import numpy as np


class Anchor(keras.layers.Layer):

    def __init__(self, base_size, ratios, scales, strides, **kwargs):
        """
        Anchor生成
        :param base_size: anchor的base_size,如：64
        :param ratios: 长宽比; 如 [1,1/2,2]
        :param scales: 缩放比: 如 [1,2,4]
        :param strides: 步长,一般为base_size的四分之一
        """
        self.base_size = base_size
        self.strides = strides
        self.ratios = ratios
        self.scales = scales

        # base anchors数量
        self.num_anchors = len(ratios) * len(scales)
        self.name = 'anchors'
        super(Anchor, self).__init__(**kwargs)

    def call(self, inputs, **kwargs):
        """

        :param inputs：输入
        input[0]: 卷积层特征(锚点所在层)，shape：[batch_size,H,W,C]
        input[1]: 图像的元数据信息, shape: [batch_size, 12 ];
        :param kwargs:
        :return:
        """
        features = inputs
        features_shape = tf.shape(features)
        print("feature_shape:{}".format(features_shape))

        # 根据feature_map生成初始anchors
        base_anchors = generate_anchors(self.base_size, self.ratios, self.scales)
        anchors = shift(features_shape[1:3], self.strides, base_anchors)

        # 扩展第一维，batch_size;每个样本都有相同的anchors
        anchors = tf.tile(tf.expand_dims(anchors, axis=0), [features_shape[0], 1, 1])

        return anchors

    def compute_output_shape(self, input_shape):
        """

        :param input_shape: [batch_size,H,W,C]
        :return:
        """
        # 计算所有的anchors数量
        total = np.prod(input_shape[1:3]) * self.num_anchors
        # total = 49 * self.num_anchors
        return (input_shape[0],
                total, 4)

def generate_anchors(base_size, ratios, scales):
    """
    根据基准尺寸、长宽比、缩放比生成边框
    :param base_size: 特征图大小 anchor的base_size,如：（64，64）
    :param ratios: 长宽比 shape:(M,)
    :param scales: 缩放比 shape:(N,)
    :return: （N*M,(y1,x1,y2,x2))
    """
    ratios = np.expand_dims(np.array(ratios), axis=1)  # (N,1)
    scales = np.expand_dims(np.array(scales), axis=0)  # (1,M)

    # 计算高度和宽度，形状为(N,M)
    h = np.sqrt(ratios) * scales * base_size
    w = 1.0 / np.sqrt(ratios) * scales * base_size

    # reshape为（N*M,1)
    h = np.reshape(h, (-1, 1))
    w = np.reshape(w, (-1, 1))

    return np.hstack([-0.5 * h, -0.5 * w, 0.5 * h, 0.5 * w])


def shift(shape, strides, base_anchors):
    """
    根据feature map的长宽，生成所有的anchors
    :param shape: （H,W)
    :param strides: 步长
    :param base_anchors:所有的基准anchors，(anchor_num,4)
    :return:
    """
    H, W = shape[0], shape[1]
    print("shape:{}".format(shape))
    ctr_x = (tf.cast(tf.range(W), tf.float32) + tf.constant(0.5, dtype=tf.float32)) * strides
    ctr_y = (tf.cast(tf.range(H), tf.float32) + tf.constant(0.5, dtype=tf.float32)) * strides

    ctr_x, ctr_y = tf.meshgrid(ctr_x, ctr_y)

    # 打平为1维,得到所有锚点的坐标
    ctr_x = tf.reshape(ctr_x, [-1])
    ctr_y = tf.reshape(ctr_y, [-1])

    #  (H*W,1,4)
    shifts = tf.expand_dims(tf.stack([ctr_y, ctr_x, ctr_y, ctr_x], axis=1), axis=1)

    # (1,anchor_num,4)
    base_anchors = tf.expand_dims(tf.constant(base_anchors, dtype=tf.float32), axis=0)

    # (H*W,anchor_num,4)
    anchors = shifts + base_anchors

    # 转为(H*W*anchor_num,4) 返回
    return tf.reshape(anchors, [-1, 4])

if __name__ == '__main__':

    sess = tf.Session()
    achrs = generate_anchors(64, [1], [1, 2, 4])
    print(achrs)
    all_achrs = shift([3, 3], 32, achrs)
    print(sess.run(tf.shape(all_achrs)))
    print(sess.run(all_achrs))
