#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author:Speciallan

import argparse
import sys

sys.path.append('../../..')


from taurus_cv.models.fsaf.io.input import get_prepared_detection_dataset
from taurus_cv.models.fsaf.networks.retinanet import retinanet as retinanet
from taurus_cv.models.fsaf.preprocessing.generator import generator
from taurus_cv.models.fsaf.training import trainer
from taurus_cv.models.fsaf.config import current_config as config
from taurus_cv.models.fsaf.layers.loss import getLoss
from taurus_cv.models.fsaf.layers.optimizer import get_optimizer

from taurus_cv.utils.spe import spe


def train(args):

    # 加载配置

    # 设置运行时环境 / training.trainer模块
    trainer.set_runtime_environment()

    # 获取VOC数据集中的训练集数据，并根据models/retinanet/config中的分类关联数据，得到最后的训练测试集 / io模块
    train_img_list = get_prepared_detection_dataset(config).get_train_data()

    print("训练集图片数量:{}".format(len(train_img_list)))

    # 生成数据，增加google数据增强
    image_size = (config.IMAGE_MAX_DIM, config.IMAGE_MAX_DIM)
    gen = generator(image_list=train_img_list, batch_size=config.BATCH_SIZE, image_size=image_size)

    t = gen.__next__()
    spe(t[0].shape, t[1].shape)

    # 构造模型，加载权重
    model = retinanet(config)
    model.load_weights(config.pretrained_weights, by_name=True)

    model.compile(loss=getLoss(), optimizer=get_optimizer(config.LEARNING_RATE), metrics=['accuracy'])

    model.fit_generator(generator=gen,
                        steps_per_epoch=len(train_img_list) // config.BATCH_SIZE,
                        epochs=args.epochs,
                        callbacks=trainer.get_callback(config))

    model.save_weights(config.retinanet_weights)

    # 训练模型并保存
    # model = trainer.train_retinanet(model, gen)

    spe(11)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', '-e', default=5, type=int, help='epochs')
    args = parser.parse_args(sys.argv[1:])

    train(args)