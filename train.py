import os
import warnings

warnings.filterwarnings("ignore")
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from torchvision import models
from torch.autograd import Variable
import matplotlib

matplotlib.use('Agg')

from resnet_yolo import resnet50, resnet18
from yoloLoss import yoloLoss
from dataset import yoloDataset
#
from visualize import Visualizer
import numpy as np
from fvcore.common.timer import Timer

CHANNEL_LAST = True
CHANNEL_LAST = False
use_gpu = torch.cuda.is_available()

file_root = './VOCdevkit/VOC2012/JPEGImages/'
learning_rate = 0.001
num_epochs = 20
batch_size = 16
net = resnet50()
# print(net)
print('load pre-trined model')
resnet = models.resnet50(pretrained=True)
new_state_dict = resnet.state_dict()
dd = net.state_dict()
for k in new_state_dict.keys():
    # print(k)
    if k in dd.keys() and not k.startswith('fc'):
        # print('yes')
        dd[k] = new_state_dict[k]
net.load_state_dict(dd)
print('cuda', torch.cuda.current_device(), torch.cuda.device_count())

criterion = yoloLoss(7, 2, 5, 0.5)
if use_gpu:
    net.cuda()
if CHANNEL_LAST:
    net = net.to(memory_format=torch.channels_last)
net.train()
# different learning rate
params = []
params_dict = dict(net.named_parameters())
for key, value in params_dict.items():
    if key.startswith('features'):
        params += [{'params': [value], 'lr': learning_rate * 1}]
    else:
        params += [{'params': [value], 'lr': learning_rate}]
optimizer = torch.optim.SGD(params, lr=learning_rate, momentum=0.9, weight_decay=5e-4)
# optimizer = torch.optim.Adam(net.parameters(),lr=learning_rate,weight_decay=1e-4)

# train_dataset = yoloDataset(root=file_root,list_file=['voc12_trainval.txt','voc07_trainval.txt'],train=True,transform = [transforms.ToTensor()] )
train_dataset = yoloDataset(root=file_root, list_file='voc12_trainval.txt', train=True,
                            transform=[transforms.ToTensor()])
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
# test_dataset = yoloDataset(root=file_root,list_file='voc07_test.txt',train=False,transform = [transforms.ToTensor()] )
test_dataset = yoloDataset(root=file_root.replace("VOC2012", "VOC2007"), list_file='voc2007test.txt', train=False,
                           transform=[transforms.ToTensor()])
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
print('the dataset has %d images' % (len(train_dataset)))
print('the batch_size is %d' % (batch_size))
logfile = open('log.txt', 'w')
num_iter = 0
vis = Visualizer(env='main')
best_test_loss = np.inf
tt = Timer()
for epoch in range(num_epochs):
    net.train()
    # if epoch == 1:
    #     learning_rate = 0.0005
    # if epoch == 2:
    #     learning_rate = 0.00075
    # if epoch == 3:
    #     learning_rate = 0.001
    if epoch == 30:
        learning_rate = 0.0001
    if epoch == 40:
        learning_rate = 0.00001
    # optimizer = torch.optim.SGD(net.parameters(),lr=learning_rate*0.1,momentum=0.9,weight_decay=1e-4)
    for param_group in optimizer.param_groups:
        param_group['lr'] = learning_rate

    print('\n\nStarting epoch %d / %d' % (epoch + 1, num_epochs))
    print('Learning Rate for this epoch: {}'.format(learning_rate))

    total_loss = 0.
    tt.reset()
    for i, (images, target) in enumerate(train_loader):
        # a,b=next(imgiter);images = Variable(a) ;target = Variable(b)
        # images = Variable(images) #torch.Size([4, 3, 448, 448])
        # target = Variable(target) #torch.Size([4, 14, 14, 30])

        if CHANNEL_LAST:
            images = images.to(memory_format=torch.channels_last)
            target = target.to(memory_format=torch.channels_last)
        if use_gpu:
            images, target = images.cuda(), target.cuda()

        pred = net(images)  # torch.Size([4, 14, 14, 30])
        loss = criterion(pred, target)  # torch.Size([])
        tloss = loss.item()
        # print(tloss)
        # total_loss += loss.data[0]
        total_loss += tloss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if (i + 1) % 5 == 0:
            print('Epoch [%d/%d], Iter [%d/%d] Loss: %.4f, average_loss: %.4f, Iter time: %.4f, and CHANNEL_LAST: %s'
                  % (epoch + 1, num_epochs, i + 1, len(train_loader), tloss, total_loss / (i + 1), tt.seconds(),str(CHANNEL_LAST)))
            num_iter += 1
            vis.plot_train_val(loss_train=total_loss / (i + 1))
            tt.reset()

    # validation
    validation_loss = 0.0
    net.eval()
    for i, (images, target) in enumerate(test_loader):
        images = Variable(images, volatile=True)
        target = Variable(target, volatile=True)
        if use_gpu:
            images, target = images.cuda(), target.cuda()

        pred = net(images)
        loss = criterion(pred, target)
        validation_loss += loss.item()
    validation_loss /= len(test_loader)
    vis.plot_train_val(loss_val=validation_loss)

    if best_test_loss > validation_loss:
        best_test_loss = validation_loss
        print('get best test loss %.5f' % best_test_loss)
        torch.save(net.state_dict(), 'best.pth')
    logfile.writelines(str(epoch) + '\t' + str(validation_loss) + '\n')
    logfile.flush()
    torch.save(net.state_dict(), 'yolo.pth')


def xx():
    i = torch.randn(3, requires_grad=False)
    t = torch.randn(3)
    mesloss = nn.MSELoss(reduction='sum')
    o = mesloss(i, t)
    ip = i.numpy()
    tp = t.numpy()
    tot = 0.
    for x in range(ip.size):
        tot += (ip[x] - tp[x]) ** 2
    print(tot)
    print(o)


def yyy():
    for i in range(100):
        a, b = next(imgiter)
        images = Variable(a)
        target = Variable(b)
        images, target = images.cuda(), target.cuda()

        pred = net(images)  # torch.Size([4, 14, 14, 30])
        loss = criterion(pred, target)  # torch.Size([])
        tloss = loss.item()
        # print(tloss)
        # total_loss += loss.data[0]
        total_loss += tloss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        vis.plot_train_val(loss_train=total_loss / (i + 1))

