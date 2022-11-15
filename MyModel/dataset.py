import glob
import random
from lib import utils
from lib.dataset import DatasetInterface
from torchvision import transforms

class MyDataset(DatasetInterface):
    def __init__(self, CONFIG):

        super(MyDataset, self).__init__(CONFIG)

        self.same_prob = CONFIG['BASE']['SAME_PROB']
        
        self.image_path_list = sorted(glob.glob('/home/jjy/Datasets/celeba/train/images/*.*'))
        self.label_path_list = sorted(glob.glob('/home/jjy/Datasets/celeba/train/label/*.*'))
        
        if CONFIG['BASE']['IS_MASTER']:
            print(f"Dataset of {self.__len__()} images constructed for the training.")

    def __getitem__(self, index):
        
        # you can use random.choice(paths) or random.sample(paths, num)

        source_color = self.pp_image(self.image_path_list[index])
        source_gray = self.pp_image(self.image_path_list[index], grayscale=True)
        source_mask = self.pp_label(self.label_path_list[index])
        
        # random_index = self.get_random_index() if random.random() < self.same_prob else index
        random_index = self.get_random_index()
        target_color = self.pp_image(self.image_path_list[random_index])
        target_gray = self.pp_image(self.image_path_list[random_index], grayscale=True)
        target_mask = self.pp_label(self.label_path_list[random_index])

        # target_flip = self.pp_image(self.image_path_list[random_index], flip=True)
        # target_flip_mask = self.pp_label(self.label_path_list[random_index], flip=True)

        return source_color, source_gray, source_mask, target_color, target_gray, target_mask

    def __len__(self):
        return len(self.image_path_list)
    
    def get_random_index(self):
        return random.randint(0, self.__len__()-1)

    def set_tf(self):

        self.tf_gray = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            # transforms.RandomHorizontalFlip(p=0.5),
            # transforms.ColorJitter(0.2, 0.2, 0.2, 0.01),
            transforms.ToTensor(),
            transforms.Normalize((0.5), (0.5))
        ])
        
        self.tf_color = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            # transforms.RandomHorizontalFlip(p=0.5),
            # transforms.ColorJitter(0.2, 0.2, 0.2, 0.01),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])