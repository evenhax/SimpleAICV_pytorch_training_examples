import os
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

from tools.path import ILSVRC2012_path

from simpleAICV.classification import backbones
from simpleAICV.classification import losses
from simpleAICV.classification.datasets.ilsvrc2012dataset import ILSVRC2012Dataset
from simpleAICV.classification.common import Opencv2PIL, TorchRandomResizedCrop, TorchRandomHorizontalFlip, RandAugment, TorchResize, TorchCenterCrop, TorchMeanStdNormalize, RandomErasing, ClassificationCollater, MixupCutmixClassificationCollater, load_state_dict

import torch
import torchvision.transforms as transforms


class config:
    network = 'vit_base_patch16'
    num_classes = 1000
    input_image_size = 224
    scale = 256 / 224

    model = backbones.__dict__[network](**{
        'image_size': 224,
        'drop_path_prob': 0.1,
        'global_pool': True,
        'num_classes': num_classes,
    })

    # load pretrained model or not
    trained_model_path = '/root/code/SimpleAICV-ImageNet-CIFAR-COCO-VOC-training/pretrained_models/masked_image_modeling_training/vit/mae-vit-base-patch16-224-epoch100-pretrain-model-loss0.399_encoder.pth'
    load_state_dict(trained_model_path,
                    model,
                    loading_new_input_size_position_encoding_weight=True)

    train_criterion = losses.__dict__['OneHotLabelCELoss']()
    test_criterion = losses.__dict__['CELoss']()

    train_dataset = ILSVRC2012Dataset(
        root_dir=ILSVRC2012_path,
        set_name='train',
        transform=transforms.Compose([
            Opencv2PIL(),
            TorchRandomResizedCrop(resize=input_image_size),
            TorchRandomHorizontalFlip(prob=0.5),
            RandAugment(magnitude=9,
                        num_layers=2,
                        resize=input_image_size,
                        mean=[0.485, 0.456, 0.406],
                        integer=True,
                        weight_idx=None,
                        magnitude_std=0.5,
                        magnitude_max=None),
            TorchMeanStdNormalize(mean=[0.485, 0.456, 0.406],
                                  std=[0.229, 0.224, 0.225]),
            RandomErasing(prob=0.25, mode='pixel', max_count=1),
        ]))

    test_dataset = ILSVRC2012Dataset(
        root_dir=ILSVRC2012_path,
        set_name='val',
        transform=transforms.Compose([
            Opencv2PIL(),
            TorchResize(resize=input_image_size * scale),
            TorchCenterCrop(resize=input_image_size),
            TorchMeanStdNormalize(mean=[0.485, 0.456, 0.406],
                                  std=[0.229, 0.224, 0.225]),
        ]))

    train_collater = MixupCutmixClassificationCollater(
        use_mixup=True,
        mixup_alpha=0.8,
        cutmix_alpha=1.0,
        cutmix_minmax=None,
        mixup_cutmix_prob=1.0,
        switch_to_cutmix_prob=0.5,
        mode='batch',
        correct_lam=True,
        label_smoothing=0.1,
        num_classes=1000)
    test_collater = ClassificationCollater()

    seed = 0
    # batch_size is total size
    batch_size = 256
    # num_workers is total workers
    num_workers = 20
    accumulation_steps = 4

    optimizer = (
        'AdamW',
        {
            # lr = base_lr:5e-4 * batch_size * accumulation_steps / 256
            'lr':
            2e-3,
            'global_weight_decay':
            False,
            # if global_weight_decay = False
            # all bias, bn and other 1d params weight set to 0 weight decay
            'weight_decay':
            5e-2,
            # lr_layer_decay only support vit style model
            'lr_layer_decay':
            0.65,
            'lr_layer_decay_block':
            model.blocks,
            'block_name':
            'blocks',
            'no_weight_decay_layer_name_list': [
                'position_encoding',
                'cls_token',
            ],
        },
    )

    scheduler = (
        'CosineLR',
        {
            'warm_up_epochs': 5,
            'min_lr': 1e-6,
        },
    )

    epochs = 100
    print_interval = 10

    sync_bn = False
    apex = True

    use_ema_model = False
    ema_model_decay = 0.9999
