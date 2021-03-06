#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
created by xuchongbo at 20171130 in Meitu.
"""

import argparse
import os
import shutil
import traceback
import time
import glob
from PIL import Image,ImageFilter
from scipy.misc import imresize
from torch.autograd import Variable
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
#torch.backends.cudnn.enabled = False
import torchvision.transforms as transforms
import torchvision
import sys
from squid import utils
from squid.metric import PSNR
import numpy as np
psnr = PSNR()

debug = False


def process(input_tensor, target_net, gpu_id=None):
    start_time = time.time()
    input_tensor = input_tensor.view(1, input_tensor.size(0), input_tensor.size(1), input_tensor.size(2))
    # if debug:
    #     print "input sum:", input_var.sum(), input_var.size()
    input_var = Variable(input_tensor, volatile=True)
    if gpu_id is not None:
        input_var = input_var.cuda()
    end_time = time.time()
    if debug:
        print " load cost:%s ms" % int((end_time-start_time)*1000)
        print "inference.."
    start_time = time.time()
    # inference
    net_outputs = target_net(input_var)

    end_time = time.time()
    if debug:
        print " cost:%s ms" % int((end_time-start_time)*1000)
    return net_outputs


def run(input_dirs, save_dir, target_net, gpu_id=None):
    if gpu_id is not None:
        print("use cuda")
        #cudnn.benchmark = True
        torch.cuda.set_device(gpu_id)
        target_net.cuda(gpu_id)
    print "input_dirs:", input_dirs
    print "save_dir:", save_dir
    if type(input_dirs) is not list:
        input_dirs = [input_dirs]  # 兼容旧config
    for input_dir in input_dirs:
        # 样本目录
        if os.path.isdir(input_dir):
            files = utils.get_files_from_dir(input_dir)
        # 样本desc.txt
        elif os.path.isfile(input_dir):
            files = utils.get_files_from_desc(input_dir)
        total = 0
        score_accumulator = 0
        img_list = read(input_dirs[0], input_dirs[0]+'test.txt')
        for index in range(len(img_list)):
            img_path,target_path = img_list[index]
            total += 1
            #read image
            img = Image.open(img_path)
            target = Image.open(target_path)
            img = img.convert('L')
            #img = img.resize((384,384))
            width, height =  img.size
            if debug:
                print width, height

            trans = transforms.Compose([transforms.ToTensor(), ])
            input_tensor = torch.from_numpy(np.array(img)).float().unsqueeze(0)
            target_tensor = torch.from_numpy(np.array(target)).float().unsqueeze(0)
            # input_tensor = trans(img)
            # target_tensor = trans(target)
            net_outputs = process(input_tensor, target_net, gpu_id)

            score = psnr(net_outputs['output'],Variable(target_tensor))
            print("Score: ",score)
            score_accumulator += score

            # for name, out in net_outputs.items():
            #     save_path = os.path.join(save_dir, os.path.basename(img_path)+'_%s.jpg' % (name,))
            #     print "save to :", save_path
            #     utils.save_tensor(out.data[0]/255.0, save_path, width, height)

        print "total: ", total
        print "PSNR: ", score_accumulator/total

def read(data_root, desc_file_path):
    import codecs
    result = []
    with codecs.open(desc_file_path, 'r', 'utf-8') as txt:
        for line in txt:
            line = line.strip()
            input_path, target_path = line.encode('utf-8').split(' ')
            if data_root:
                input_path  = os.path.join(data_root, input_path)
                target_path = os.path.join(data_root, target_path)
            result.append((input_path, target_path))
        print "read from {} total {} ".format(desc_file_path, len(result))
    return result

if __name__ == "__main__":
    debug = True
    config = utils.load_config(sys.argv[1])
    test_snapshot_path = sys.argv[2]
    checkpoint = torch.load(test_snapshot_path, map_location=lambda storage, loc: storage)
    print checkpoint.keys()
    config.target_net.load_state_dict(checkpoint)
    config.target_net.eval()
    run(config.test_input_dir, config.TEST_OUT_FOLDER, config.target_net, config.GPU_ID)
