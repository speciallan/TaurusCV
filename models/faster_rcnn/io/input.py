#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author:Speciallan

"""
模型的输入
"""

import numpy as np
from datasets.pascal_voc import get_voc_dataset

class Dataset(object):
    """
    基础数据集
    """

    def __init__(self, stage='train', class_mapping=None):

        self.stage = stage
        self.class_mapping = class_mapping

        # 图像信息字典列表，包含的key有boxes,labels,filename,filepath,type等
        self.image_info_list = []

    def get_image_info_list(self):
        return self.image_info_list

    def prepare(self):
        """
        将数据集转为标准的目标检测数据集格式
        :return:
        """
        raise NotImplementedError('num_classes method not implemented')

class VocDataset(Dataset):

    def __init__(self, voc_path, **kwargs):
        """
        VOC数据集初始化
        :param voc_path: 数据集路径
        :param kwargs:
        """
        self.voc_path = voc_path
        super(VocDataset, self).__init__(**kwargs)

    def prepare(self):

        img_info_list, classes_count, class_mapping = get_voc_dataset(self.voc_path, self.class_mapping)

        for img_info in img_info_list:
            image_info = {"filename": img_info['filename'],
                          "filepath": img_info['filepath'],
                          "type": img_info['imageset']}
            # GT 边框转换
            boxes = []
            labels = []
            # 训练阶段加载边框标注信息
            if self.stage == 'train':
                for bbox in img_info['bboxes']:
                    y1, x1, y2, x2 = bbox['y1'], bbox['x1'], bbox['y2'], bbox['x2']
                    boxes.append([y1, x1, y2, x2])
                    labels.append(bbox['class_id'])

            image_info['boxes'] = np.array(boxes)
            image_info['labels'] = np.array(labels)
            self.image_info_list.append(image_info)
