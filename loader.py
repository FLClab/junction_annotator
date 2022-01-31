from skimage import io
from matplotlib import pyplot as plt
import numpy as np
import os

class Loader:
    def __init__(self, path, crop_size=512, crop_step=int(512*0.75)):
        """
        Crop iterator
        :param path:
        :param crop_size:
        :param crop_step:
        """
        self.path = path
        self.files = os.listdir(path)

        self.crop_size = crop_size
        self.crop_step = crop_step

        self.file_idx = 0
        self.n = 0

        self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))

    def load_image(self, img_path):
        """
        Load the image of the given index, turns it into uint8 RGB for display
        :param file_idx: index of the image in self.files
        :return: Image with shape [height, width, color]
        """
        self.image = io.imread(img_path).astype('float32')
        self.image[0] = self.image[0] - np.min(self.image[0], axis=0)
        self.image[1] = self.image[1] - np.min(self.image[1], axis=0)
        self.image[0] = self.image[0] / np.percentile(self.image[0], 99.9)
        self.image[1] = self.image[1] / np.percentile(self.image[1], 99.9)
        self.image = np.clip(self.image, 0, 1)
        self.image = (self.image*255).astype('uint8')

        self.image = np.concatenate((self.image, np.zeros((1,self.image.shape[1], self.image.shape[2]), dtype='uint8')), axis=0)
        self.image = np.moveaxis(self.image, 0, -1)
        buffer = self.image[:,:,1].copy()
        self.image[:,:,1] = self.image[:,:,0].copy()
        self.image[:,:,0] = buffer

    def generate_crops(self, img_path):
        self.load_image(img_path)
        self.crop_data = []
        for j in range(0, self.image.shape[0], self.crop_step):
            for i in range(0, self.image.shape[1], self.crop_step):
                self.crop_data.append({'image':img_path, 'Y':j, 'X':i, 'size':self.crop_size})

        np.random.shuffle(self.crop_data)

    def __iter__(self):
        return self

    def __next__(self):
        if self.file_idx >= len(self.files):
            raise StopIteration

        crop = self.crop_data[self.n]
        y = crop['Y']
        x = crop['X']
        size = crop['size']
        crop = self.image[y:y+size, x:x+size].copy()

        if crop.shape[0] != crop.shape[1]:
            canvas = np.zeros((self.crop_size, self.crop_size, 3), dtype='uint8')
            canvas[:crop.shape[0], :crop.shape[1], :] = crop
            crop = canvas

        self.n += 1

        if self.n > len(self.crop_data):
            self.file_idx += 1
            self.x = 0
            self.y = 0
            if self.file_idx < len(self.files):
                self.n = 0
                self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))


        return crop

if __name__=='__main__':
    data_path = 'example_image'
    loader = Loader(data_path)
    for l in loader:
        pass
